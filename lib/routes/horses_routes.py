import logging
import os
from datetime import datetime
from uuid import uuid4
from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

from werkzeug.datastructures import FileStorage
from lib.models import Client, ClientHorse, Horse, db
from PIL import Image
import io

horses_bp = Blueprint('horses', __name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATIC_FOLDER_REL = os.path.join('lib', 'static')
IMAGES_FOLDER_REL = os.path.join(STATIC_FOLDER_REL, 'images')
PROFILE_PICS_FOLDER_REL = os.path.join(IMAGES_FOLDER_REL, 'horse_profile')
LIMBS_PICS_FOLDER_REL = os.path.join(IMAGES_FOLDER_REL, 'horse_limbs')


profile_PicturesFolder = os.path.join(project_root, PROFILE_PICS_FOLDER_REL)
limbs_PicturesFolder = os.path.join(project_root, LIMBS_PICS_FOLDER_REL)


os.makedirs(profile_PicturesFolder, exist_ok=True)
os.makedirs(limbs_PicturesFolder, exist_ok=True)
logger.info(f"Profile pictures folder: {profile_PicturesFolder}")
logger.info(f"Limb pictures folder: {limbs_PicturesFolder}")



def _get_image_url(filename, image_type):
    """Generates the absolute URL for a horse image."""
    if not filename:
        return None
    try:
        if image_type == 'profile':
            relative_path = os.path.join('images', 'horse_profile', filename).replace('\\', '/')
            return url_for('static', filename=relative_path, _external=True)
        elif image_type == 'limb':
            relative_path = os.path.join('images', 'horse_limbs', filename).replace('\\', '/')
            return url_for('static', filename=relative_path, _external=True)
        else:
            return None
    except RuntimeError as e:
        logger.error(f"Error generating URL for {filename} (type: {image_type}): {e}")
        return None


def _save_horse_image_from_filestorage(image_file: FileStorage, horse_id, image_type_prefix, target_folder):
    """
    Reads image data from a FileStorage object, saves it as WEBP with a unique name.
    Returns the generated filename or raises ValueError.
    """
    if not image_file or not image_file.filename:
        raise ValueError("Missing image file or filename.")

    try:

        safe_original = secure_filename(image_file.filename)
        unique_filename = f"{horse_id}_{image_type_prefix}_{uuid4()}.webp"
        save_path = os.path.join(target_folder, unique_filename)


        with Image.open(image_file.stream) as img:

            img.save(save_path, "WEBP", quality=85)

        logger.info(f"Saved image for horse {horse_id} to {save_path}")
        return unique_filename

    except Exception as e:

        logger.exception(f"Failed to save image for horse {horse_id}, type {image_type_prefix}: {e}")
        raise ValueError(f"Could not process or save image for {image_type_prefix}. Invalid image format?")


def _delete_horse_image(filename, target_folder):
    """Deletes an image file if it exists."""
    if not filename:
        return False
    try:
        path = os.path.join(target_folder, filename)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted image file: {path}")
            return True
        else:
            logger.warning(f"Attempted to delete non-existent image file: {path}")
            return False
    except OSError as e:
        logger.error(f"Error deleting image file {path}: {e}")
        return False



@horses_bp.route('/horses', methods=['GET'])
@jwt_required()
def get_horses():
    """Gets a list of all horses with image URLs. (Uses JSON response)"""
    try:
        horses = Horse.query.order_by(Horse.name).all()
        horses_list = [{
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": _get_image_url(horse.profilePicturePath, 'profile'),
            "birthDate": horse.birthDate.isoformat() if horse.birthDate else None,
            "pictureRightFrontPath": _get_image_url(horse.pictureRightFrontPath, 'limb'),
            "pictureLeftFrontPath": _get_image_url(horse.pictureLeftFrontPath, 'limb'),
            "pictureRightHindPath": _get_image_url(horse.pictureRightHindPath, 'limb'),
            "pictureLeftHindPath": _get_image_url(horse.pictureLeftHindPath, 'limb')
        } for horse in horses]

        return jsonify(horses_list), 200

    except Exception as e:
        logger.exception("Server error getting all horses.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@horses_bp.route('/horse/<int:horse_id>', methods=['GET'])
@jwt_required()
def get_horse_by_id(horse_id):
    """Gets details for a single horse using the ID from the URL."""
    try:
        horse = Horse.query.get_or_404(horse_id, description=f"Horse with id {horse_id} not found.")
        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": _get_image_url(horse.profilePicturePath, 'profile'),
            "birthDate": horse.birthDate.isoformat() if horse.birthDate else None,
            "pictureRightFrontPath": _get_image_url(horse.pictureRightFrontPath, 'limb'),
            "pictureLeftFrontPath": _get_image_url(horse.pictureLeftFrontPath, 'limb'),
            "pictureRightHindPath": _get_image_url(horse.pictureRightHindPath, 'limb'),
            "pictureLeftHindPath": _get_image_url(horse.pictureLeftHindPath, 'limb')
        }), 200
    except NotFound as e:

        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting horse {horse_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@horses_bp.route('/horse/<int:horse_id>', methods=['PUT'])
@jwt_required()
def update_horse(horse_id):
    """
    Handles PUT for a single horse identified by ID in URL.
    Expects multipart/form-data:
        - 'name' (optional form field)
        - 'birthDate' (optional form field, YYYY-MM-DD or empty string to clear)
        - image files (optional, e.g., 'profilePicture', 'pictureRightFront', etc.)
        - To remove an image on PUT, send a specific form field like 'remove_profilePicture=true'.
    """
    try:

        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data for PUT.")


        horse = Horse.query.get_or_404(horse_id, description=f"Horse with id {horse_id} not found.")
        updated = False


        if 'name' in request.form:
            new_name = request.form.get('name')
            if not new_name or new_name.strip() == "":
                raise BadRequest("Horse name cannot be empty.")
            if horse.name != new_name:
                horse.name = new_name
                updated = True


        if 'birthDate' in request.form:
            birth_date_str = request.form.get('birthDate')
            new_birth_date = None

            if birth_date_str is not None and birth_date_str.strip() != "":
                try:
                    new_birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    raise BadRequest("Invalid birthDate format. Use YYYY-MM-DD or send empty string to clear.")

            current_birth_date = horse.birthDate.date() if isinstance(horse.birthDate, datetime) else horse.birthDate
            if current_birth_date != new_birth_date:
                horse.birthDate = new_birth_date
                updated = True



        image_fields_map = {
            'profilePicture': ('profilePicturePath', profile_PicturesFolder, 'profile'),
            'pictureRightFront': ('pictureRightFrontPath', limbs_PicturesFolder, 'right_front'),
            'pictureLeftFront': ('pictureLeftFrontPath', limbs_PicturesFolder, 'left_front'),
            'pictureRightHind': ('pictureRightHindPath', limbs_PicturesFolder, 'right_hind'),
            'pictureLeftHind': ('pictureLeftHindPath', limbs_PicturesFolder, 'left_hind'),
        }

        for form_key, (path_attr, folder, type_prefix) in image_fields_map.items():
            image_file = request.files.get(form_key)
            remove_flag_key = f"remove_{form_key}"
            remove_flag = request.form.get(remove_flag_key, 'false').lower() == 'true'
            old_filename = getattr(horse, path_attr)

            if image_file:
                try:
                    new_filename = _save_horse_image_from_filestorage(image_file, horse.id, type_prefix, folder)
                    setattr(horse, path_attr, new_filename)
                    updated = True

                    _delete_horse_image(old_filename, folder)
                except ValueError as e:
                    raise BadRequest(str(e))

            elif remove_flag:
                if old_filename:
                    if _delete_horse_image(old_filename, folder):
                        setattr(horse, path_attr, None)
                        updated = True
                    else:
                        logger.error(f"Failed to delete image file {old_filename} during update for horse {horse_id}")


        if not updated:
            return jsonify({"message": "No fields provided or values unchanged."}), 200

        db.session.commit()
        logger.info(f"Horse {horse_id} updated.")

        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": _get_image_url(horse.profilePicturePath, 'profile'),
            "birthDate": horse.birthDate.isoformat() if horse.birthDate else None,
            "pictureRightFrontPath": _get_image_url(horse.pictureRightFrontPath, 'limb'),
            "pictureLeftFrontPath": _get_image_url(horse.pictureLeftFrontPath, 'limb'),
            "pictureRightHindPath": _get_image_url(horse.pictureRightHindPath, 'limb'),
            "pictureLeftHindPath": _get_image_url(horse.pictureLeftHindPath, 'limb')
        }), 200

    except (NotFound, BadRequest, UnsupportedMediaType) as e:
         db.session.rollback()
         logger.warning(f"Client error updating horse {horse_id}: {e}")
         return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error updating horse {horse_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@horses_bp.route('/horse/<int:horse_id>', methods=['DELETE'])
@jwt_required()
def delete_horse(horse_id):
    """Deletes a horse and its images using the ID from the URL."""
    try:
        horse = Horse.query.get_or_404(horse_id, description=f"Horse with id {horse_id} not found.")


        filenames_to_delete = [
            (horse.profilePicturePath, profile_PicturesFolder),
            (horse.pictureRightFrontPath, limbs_PicturesFolder),
            (horse.pictureLeftFrontPath, limbs_PicturesFolder),
            (horse.pictureRightHindPath, limbs_PicturesFolder),
            (horse.pictureLeftHindPath, limbs_PicturesFolder),
        ]

        db.session.delete(horse)
        db.session.commit()
        logger.info(f"Horse {horse_id} deleted from database.")


        for filename, folder in filenames_to_delete:
            _delete_horse_image(filename, folder)

        return jsonify({"message": "Horse deleted successfully"}), 200

    except NotFound as e:
         db.session.rollback()
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error deleting horse {horse_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@horses_bp.route('/horse', methods=['POST'])
@jwt_required()
def add_horse():
    """
    Adds a new horse. Expects multipart/form-data.
    Requires 'name' (form field). Optional 'birthDate' (form field, YYYY-MM-DD or empty string).
    Optional image files: 'profilePicture', 'pictureRightFront', 'pictureLeftFront',
                          'pictureRightHind', 'pictureLeftHind'.
    """
    try:

        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        name = request.form.get('name')
        if not name or name.strip() == "":
            raise BadRequest("Horse name form field is required and cannot be empty.")


        birth_date_str = request.form.get('birthDate')
        birth_date = None

        if birth_date_str is not None and birth_date_str.strip() != "":
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                raise BadRequest("Invalid birthDate format. Use YYYY-MM-DD or send empty string.")



        horse = Horse(
            name=name,
            birthDate=birth_date
        )
        db.session.add(horse)
        db.session.flush()
        logger.info(f"Horse object created with temporary ID {horse.id}")


        image_fields_to_save = {}
        image_fields_map = {
            'profilePicture': ('profilePicturePath', profile_PicturesFolder, 'profile'),
            'pictureRightFront': ('pictureRightFrontPath', limbs_PicturesFolder, 'right_front'),
            'pictureLeftFront': ('pictureLeftFrontPath', limbs_PicturesFolder, 'left_front'),
            'pictureRightHind': ('pictureRightHindPath', limbs_PicturesFolder, 'right_hind'),
            'pictureLeftHind': ('pictureLeftHindPath', limbs_PicturesFolder, 'left_hind'),
        }

        for form_key, (path_attr, folder, type_prefix) in image_fields_map.items():
             image_file = request.files.get(form_key)
             if image_file:
                 try:
                     saved_filename = _save_horse_image_from_filestorage(image_file, horse.id, type_prefix, folder)
                     image_fields_to_save[path_attr] = saved_filename
                 except ValueError as e:
                     db.session.rollback()
                     raise BadRequest(str(e))
                 except Exception as e:
                     db.session.rollback()
                     logger.exception(f"Unexpected error saving {type_prefix} image for new horse.")
                     raise Exception(f"Failed to process {type_prefix} image.")


        for attr, filename in image_fields_to_save.items():
            setattr(horse, attr, filename)


        db.session.commit()
        logger.info(f"Horse {horse.id} created and committed successfully.")


        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": _get_image_url(horse.profilePicturePath, 'profile'),
            "birthDate": horse.birthDate.isoformat() if horse.birthDate else None,
            "pictureRightFrontPath": _get_image_url(horse.pictureRightFrontPath, 'limb'),
            "pictureLeftFrontPath": _get_image_url(horse.pictureLeftFrontPath, 'limb'),
            "pictureRightHindPath": _get_image_url(horse.pictureRightHindPath, 'limb'),
            "pictureLeftHindPath": _get_image_url(horse.pictureLeftHindPath, 'limb')
        }), 201

    except (BadRequest, NotFound, UnsupportedMediaType) as e:
        db.session.rollback()
        logger.warning(f"Client error adding horse: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Server error adding horse.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@horses_bp.route('/horse/<int:horse_id>/clients', methods=['GET'])
@jwt_required()
def get_horse_clients(horse_id):
    """
    Gets the list of clients associated with a specific horse,
    identified by the ID in the URL path.
    """
    try:

        horse = Horse.query.get_or_404(horse_id, description=f"Horse with id {horse_id} not found.")

        clients_list = []

        associations = ClientHorse.query.filter_by(horseId=horse_id).all()
        for assoc in associations:
            client = Client.query.get(assoc.clientId)
            if client:
                clients_list.append({
                    "idClient": client.id,
                    "name": client.name,
                    "email": client.email,
                    "phoneCountryCode": client.phoneCountryCode,
                    "phoneNumber": client.phoneNumber,
                    "isOwner": assoc.isClientHorseOwner
                })

        return jsonify(clients_list), 200

    except NotFound as e:

         logger.warning(f"Client error getting horse clients for horse {horse_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting clients for horse {horse_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500
