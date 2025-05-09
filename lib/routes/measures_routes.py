import logging
import os
import random
import uuid
import json
from datetime import datetime

from flask import Blueprint, jsonify, request, url_for
from flask_jwt_extended import jwt_required
from lib.models import Appointment, Horse, Measure, Veterinarian, db
from PIL import Image

from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from ..predict.predict import calculate_body_score # Import the new function

measures_bp = Blueprint('measures', __name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATIC_FOLDER_REL = os.path.join('lib', 'static')
MEASURES_FOLDER_REL = os.path.join(STATIC_FOLDER_REL, 'measures')


measures_PicturesFolder = os.path.join(project_root, MEASURES_FOLDER_REL)


os.makedirs(measures_PicturesFolder, exist_ok=True)
logger.info(f"Measures pictures folder: {measures_PicturesFolder}")



def _get_measure_image_url(filename):
    """Generates the absolute URL for a measure image."""
    if not filename:
        return None
    try:

        relative_path = os.path.join('measures', filename).replace('\\', '/')
        return url_for('static', filename=relative_path, _external=True)
    except RuntimeError as e:
        logger.error(f"Error generating URL for measure image {filename}: {e}")
        return None


def _save_measure_image_from_filestorage(image_file: FileStorage, measure_id, horse_id):
    """
    Reads image data from a FileStorage object, saves it (e.g., as WEBP) with a unique name.
    Returns the generated filename or raises ValueError.
    """
    if not image_file or not image_file.filename:
        raise ValueError("Missing image file or filename.")

    try:

        unique_filename = f"{measure_id}_measure_{horse_id}_horseId_{uuid.uuid4()}.webp"
        save_path = os.path.join(measures_PicturesFolder, unique_filename)


        with Image.open(image_file.stream) as img:

            img.save(save_path, "WEBP", quality=85)

        logger.info(f"Saved image for measure {measure_id} to {save_path}")
        return unique_filename

    except Exception as e:
        logger.exception(f"Failed to save image for measure {measure_id}: {e}")
        raise ValueError("Could not process or save measure image. Invalid format?")


def _delete_measure_image(filename):
    """Deletes a measure image file if it exists."""
    if not filename:
        return False
    try:
        path = os.path.join(measures_PicturesFolder, filename)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted measure image file: {path}")
            return True
        else:
            logger.warning(f"Attempted to delete non-existent measure image file: {path}")
            return False
    except OSError as e:
        logger.error(f"Error deleting measure image file {path}: {e}")
        return False


def forward_coordinates(coordinates_list_of_dicts):
    """
    Processes coordinates to get algorithm-derived body weight (placeholder)
    and body condition score (from prediction model).

    Args:
        coordinates_list_of_dicts (list): A list of dictionaries,
                                          e.g., [{'x': x1, 'y': y1}, ..., {'x': x14, 'y': y14}].
                                          Expected to contain 14 points.
    Returns:
        dict: A dictionary with 'algorithmBW', 'algorithmBCS', and optionally 'error'.
    """
    logger.info(f"Attempting to process coordinates: {coordinates_list_of_dicts}")

    # Body Weight is still a placeholder
    algo_bw = random.randint(500, 800)
    algo_bcs = None
    error_message = None

    if not coordinates_list_of_dicts or not isinstance(coordinates_list_of_dicts, list):
        logger.info("No coordinates provided or not in list format.")
        return {'algorithmBW': algo_bw, 'algorithmBCS': algo_bcs}

    flat_coordinates = []
    for i, point_dict in enumerate(coordinates_list_of_dicts):
        if isinstance(point_dict, dict) and 'x' in point_dict and 'y' in point_dict:
            try:
                flat_coordinates.append(float(point_dict['x']))
                flat_coordinates.append(float(point_dict['y']))
            except (ValueError, TypeError) as e:
                error_message = f"Invalid coordinate value for point {i}: {point_dict}. Error: {e}"
                logger.error(error_message)
                return {'algorithmBW': algo_bw, 'algorithmBCS': None, 'error': error_message}
        else:
            error_message = f"Malformed coordinate entry at index {i}: {point_dict}. Expected dict with 'x' and 'y'."
            logger.error(error_message)
            return {'algorithmBW': algo_bw, 'algorithmBCS': None, 'error': error_message}

    if len(flat_coordinates) == 28: # Expect 14 points * 2 coordinates each
        try:
            predicted_bcs = calculate_body_score(flat_coordinates)
            algo_bcs = predicted_bcs # Already a float from calculate_body_score
            logger.info(f"Successfully calculated Body Score: {algo_bcs}")
        except ValueError as e: # Catch errors from calculate_body_score (e.g., wrong number of inputs, math errors)
            error_message = f"Error calculating body score: {e}"
            logger.error(error_message)
        except FileNotFoundError as e: # Catch if model/scaler files are missing (should be caught at startup of predict.py)
            error_message = f"Model/Scaler file not found for BCS calculation: {e}"
            logger.error(error_message)
            # This is a server configuration error, might warrant a different handling
        except Exception as e:
            error_message = f"Unexpected error during body score calculation: {e}"
            logger.exception(error_message) # Use logger.exception to include stack trace
    elif len(flat_coordinates) > 0:
        error_message = f"Expected 28 coordinate values (14 pairs), but received {len(flat_coordinates)} from {len(coordinates_list_of_dicts)} points."
        logger.warning(error_message)
    else: # flat_coordinates is empty, meaning coordinates_list_of_dicts was empty or malformed early
        logger.info("No valid coordinates to process for BCS.")

    result = {'algorithmBW': algo_bw, 'algorithmBCS': algo_bcs}
    if error_message:
        result['error'] = error_message

    return {
        'algorithmBW': algo_bw,
        'algorithmBCS': algo_bcs
    }



@measures_bp.route('/measure', methods=['POST'])
@jwt_required()
def add_measure():
    """
    Adds a new measure. Expects multipart/form-data.
    Required form fields: 'horseId', 'date' (YYYY-MM-DD or ISO format).
    Optional form fields: 'veterinarianId', 'appointmentId',
                          'coordinates' (JSON string representing a LIST of objects),
                          'userBW', 'userBCS', 'favorite' ('true'/'false').
    Optional file upload: 'picture'.
    """
    try:

        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")


        horse_id_str = request.form.get('horseId')
        date_str = request.form.get('date')

        try:
            if horse_id_str is None: raise ValueError("'horseId' form field is required.")
            horse_id = int(horse_id_str)
            if not date_str: raise ValueError("'date' form field is required.")

            try:
                measure_date = datetime.fromisoformat(date_str)
            except ValueError:
                measure_date = datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError) as ve:
             raise BadRequest(f"Invalid or missing required form field: {ve}")


        veterinarian_id = request.form.get('veterinarianId', type=int, default=None)
        appointment_id = request.form.get('appointmentId', type=int, default=None)
        coordinates_str = request.form.get('coordinates')
        user_bw = request.form.get('userBW', type=int, default=None)
        user_bcs = request.form.get('userBCS', type=int, default=None)
        favorite_str = request.form.get('favorite', 'false')
        picture_file = request.files.get('picture')


        if not Horse.query.get(horse_id):
            raise NotFound(f"Horse with id {horse_id} not found.")
        if veterinarian_id and not Veterinarian.query.get(veterinarian_id):
            raise NotFound(f"Veterinarian with id {veterinarian_id} not found.")
        if appointment_id and not Appointment.query.get(appointment_id):
            raise NotFound(f"Appointment with id {appointment_id} not found.")


        coordinates = None
        if coordinates_str:
            try:

                coordinates = json.loads(coordinates_str)
                if not isinstance(coordinates, list):
                    raise ValueError("'coordinates' must be a valid JSON string representing a list of objects.")


            except (json.JSONDecodeError, ValueError) as e:
                raise BadRequest(f"Invalid 'coordinates' format: {e}")


        measure = Measure(
            horseId=horse_id,
            date=measure_date,
            veterinarianId=veterinarian_id,
            appointmentId=appointment_id,
            coordinates=coordinates,
            userBW=user_bw,
            userBCS=user_bcs,

        )
        db.session.add(measure)
        db.session.flush()


        saved_picture_filename = None
        algo_bw = None
        algo_bcs = None


        if coordinates:
            try:
                results = forward_coordinates(coordinates)
                if results.get('error'):
                    logger.error(f"Coordinate processing failed for new measure: {results['error']}")
                    # Decide if this should be a BadRequest or if measure can be saved without BCS
                    # For now, allow saving without BCS, but log the error.
                    # If coordinates were provided with the intent of calculation, client might expect an error.
                    # Consider: raise BadRequest(f"Coordinate processing error: {results['error']}")
                    algo_bw = results.get('algorithmBW') # BW might still be generated
                    algo_bcs = None
                else:
                    algo_bw = results.get('algorithmBW')
                    algo_bcs = results.get('algorithmBCS')
                measure.algorithmBW = algo_bw
                measure.algorithmBCS = algo_bcs
            except Exception as e:
                logger.error(f"Failed to process coordinates for measure {measure.id}: {e}")

        if picture_file:
            try:
                saved_picture_filename = _save_measure_image_from_filestorage(picture_file, measure.id, horse_id)
                measure.picturePath = saved_picture_filename
            except ValueError as e:
                 db.session.rollback()
                 raise BadRequest(str(e))
            except Exception as e:
                 db.session.rollback()
                 logger.exception(f"Unexpected error saving measure image for measure {measure.id}.")
                 raise Exception("Failed to process measure image.")


        db.session.commit()
        logger.info(f"Measure {measure.id} created successfully.")


        return jsonify({
            "message": "Measure added successfully",
            "measure": {
                "idMeasure": measure.id,
                "horseId": measure.horseId,
                "date": measure.date.isoformat(),
                "veterinarianId": measure.veterinarianId,
                "appointmentId": measure.appointmentId,
                "coordinates": measure.coordinates,
                "userBW": measure.userBW,
                "userBCS": measure.userBCS,
                "algorithmBW": measure.algorithmBW,
                "algorithmBCS": measure.algorithmBCS,
                "favorite": measure.favorite,
                "picturePath": _get_measure_image_url(measure.picturePath)
            }
        }), 201

    except (BadRequest, NotFound, UnsupportedMediaType) as e:
        db.session.rollback()
        logger.warning(f"Client error adding measure: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Server error adding measure.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@measures_bp.route('/measures', methods=['GET'])
@jwt_required()
def get_measures():
    """Gets a list of all measures."""
    try:
        measures = Measure.query.order_by(Measure.date.desc()).all()
        measures_list = [{
            'id': measure.id,
            'horseId': measure.horseId,
            'date': measure.date.isoformat(),
            'veterinarianId': measure.veterinarianId,
            'appointmentId': measure.appointmentId,
            'coordinates': measure.coordinates,
            'userBW': measure.userBW,
            'userBCS': measure.userBCS,
            'algorithmBW': measure.algorithmBW,
            'algorithmBCS': measure.algorithmBCS,
            'favorite': measure.favorite,
            'picturePath': _get_measure_image_url(measure.picturePath)
        } for measure in measures]

        return jsonify(measures_list), 200

    except Exception as e:
        logger.exception("Server error getting all measures.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@measures_bp.route('/measures/horse/<int:horse_id>', methods=['GET'])
@jwt_required()
def get_measures_by_horse(horse_id):
    """Gets measures filtered by horse ID from URL."""
    try:
        if not Horse.query.get(horse_id):
             raise NotFound(f"Horse with id {horse_id} not found.")

        measures = Measure.query.filter_by(horseId=horse_id).order_by(Measure.date.desc()).all()

        measures_list = [{
            'id': measure.id,
            'horseId': measure.horseId,
            'date': measure.date.isoformat(),
            'veterinarianId': measure.veterinarianId,
            'appointmentId': measure.appointmentId,
            'coordinates': measure.coordinates,
            'userBW': measure.userBW,
            'userBCS': measure.userBCS,
            'algorithmBW': measure.algorithmBW,
            'algorithmBCS': measure.algorithmBCS,
            'favorite': measure.favorite,
            'picturePath': _get_measure_image_url(measure.picturePath)
        } for measure in measures]

        return jsonify(measures_list), 200

    except NotFound as e:
         logger.warning(f"Client error getting measures for horse {horse_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting measures for horse {horse_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@measures_bp.route('/measures/appointment/<int:appointment_id>', methods=['GET'])
@jwt_required()
def get_measures_by_appointment(appointment_id):
    """Gets measures filtered by appointment ID from URL."""
    try:
        if not Appointment.query.get(appointment_id):
             raise NotFound(f"Appointment with id {appointment_id} not found.")

        measures = Measure.query.filter_by(appointmentId=appointment_id).order_by(Measure.date.desc()).all()

        measures_list = [{
            'id': measure.id,
            'horseId': measure.horseId,
            'date': measure.date.isoformat(),
            'veterinarianId': measure.veterinarianId,
            'appointmentId': measure.appointmentId,
            'coordinates': measure.coordinates,
            'userBW': measure.userBW,
            'userBCS': measure.userBCS,
            'algorithmBW': measure.algorithmBW,
            'algorithmBCS': measure.algorithmBCS,
            'favorite': measure.favorite,
            'picturePath': _get_measure_image_url(measure.picturePath)
        } for measure in measures]

        return jsonify(measures_list), 200

    except NotFound as e:
         logger.warning(f"Client error getting measures for appointment {appointment_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting measures for appointment {appointment_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@measures_bp.route('/measure/<int:measure_id>', methods=['GET'])
@jwt_required()
def get_measure_by_id(measure_id):
    """Gets details for a single measure using the ID from the URL."""
    try:
        measure = Measure.query.get_or_404(measure_id, description=f"Measure with id {measure_id} not found.")
        return jsonify({
            'id': measure.id,
            'horseId': measure.horseId,
            'date': measure.date.isoformat(),
            'veterinarianId': measure.veterinarianId,
            'appointmentId': measure.appointmentId,
            'coordinates': measure.coordinates,
            'userBW': measure.userBW,
            'userBCS': measure.userBCS,
            'algorithmBW': measure.algorithmBW,
            'algorithmBCS': measure.algorithmBCS,
            'favorite': measure.favorite,
            'picturePath': _get_measure_image_url(measure.picturePath)
        }), 200
    except NotFound as e:
        logger.warning(f"Client error getting measure {measure_id}: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting measure {measure_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@measures_bp.route('/measure/<int:measure_id>', methods=['PUT'])
@jwt_required()
def update_measure(measure_id):
    """
    Updates an existing measure identified by ID in URL.
    Expects multipart/form-data.
    Optional form fields: 'horseId', 'date', 'veterinarianId', 'appointmentId',
                          'coordinates' (JSON string representing a LIST of objects),
                          'userBW', 'userBCS', 'favorite' ('true'/'false').
    Optional file upload: 'picture'.
    To remove picture, send form field 'remove_picture=true'.
    """
    try:

        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data for PUT.")


        measure = Measure.query.get_or_404(measure_id, description=f"Measure with id {measure_id} not found.")
        updated = False
        recalculate_algo = False


        if 'horseId' in request.form:
            try:
                new_horse_id = request.form.get('horseId', type=int)
                if new_horse_id is None: raise ValueError("horseId cannot be empty if provided.")
                if not Horse.query.get(new_horse_id):
                    raise NotFound(f"Horse with id {new_horse_id} not found.")
                if measure.horseId != new_horse_id:
                    measure.horseId = new_horse_id
                    updated = True
            except (ValueError, TypeError):
                raise BadRequest("Invalid horseId format.")

        if 'date' in request.form:
            date_str = request.form.get('date')
            if not date_str: raise BadRequest("'date' cannot be empty.")
            try:
                try:
                    parsed_date = datetime.fromisoformat(date_str)
                except ValueError:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                current_date_val = measure.date.date() if isinstance(measure.date, datetime) else measure.date
                new_date_val = parsed_date.date()
                if current_date_val != new_date_val:
                    measure.date = parsed_date
                    updated = True
            except (ValueError, TypeError):
                raise BadRequest("Invalid date format. Use ISO format or YYYY-MM-DD.")


        if 'veterinarianId' in request.form:
            vet_id_str = request.form.get('veterinarianId')
            new_vet_id = None
            if vet_id_str is not None and vet_id_str.strip() != "":
                try:
                    new_vet_id = int(vet_id_str)
                    if not Veterinarian.query.get(new_vet_id):
                        raise NotFound(f"Veterinarian with id {new_vet_id} not found.")
                except (ValueError, TypeError):
                    raise BadRequest("Invalid veterinarianId format.")
            if measure.veterinarianId != new_vet_id:
                measure.veterinarianId = new_vet_id
                updated = True

        if 'appointmentId' in request.form:
            app_id_str = request.form.get('appointmentId')
            new_app_id = None
            if app_id_str is not None and app_id_str.strip() != "":
                try:
                    new_app_id = int(app_id_str)
                    if not Appointment.query.get(new_app_id):
                        raise NotFound(f"Appointment with id {new_app_id} not found.")
                except (ValueError, TypeError):
                    raise BadRequest("Invalid appointmentId format.")
            if measure.appointmentId != new_app_id:
                measure.appointmentId = new_app_id
                updated = True

        if 'userBW' in request.form:
            try:

                bw_str = request.form.get('userBW')
                new_bw = int(bw_str) if bw_str and bw_str.strip() else None
                if measure.userBW != new_bw:
                    measure.userBW = new_bw
                    updated = True
            except (ValueError, TypeError):
                 raise BadRequest("Invalid userBW format, must be an integer or empty.")

        if 'userBCS' in request.form:
            try:

                bcs_str = request.form.get('userBCS')
                new_bcs = int(bcs_str) if bcs_str and bcs_str.strip() else None
                if measure.userBCS != new_bcs:
                    measure.userBCS = new_bcs
                    updated = True
            except (ValueError, TypeError):
                 raise BadRequest("Invalid userBCS format, must be an integer or empty.")


        if 'coordinates' in request.form:
            coordinates_str = request.form.get('coordinates')
            new_coordinates = None

            if coordinates_str is not None and coordinates_str.strip() != "":
                try:

                    new_coordinates = json.loads(coordinates_str)
                    if not isinstance(new_coordinates, list):
                        raise ValueError("'coordinates' must be a valid JSON string representing a list of objects.")

                except (json.JSONDecodeError, ValueError) as e:
                    raise BadRequest(f"Invalid 'coordinates' format: {e}")



            if json.dumps(measure.coordinates) != json.dumps(new_coordinates):
                measure.coordinates = new_coordinates
                updated = True
                if new_coordinates:
                    recalculate_algo = True
                else:
                    measure.algorithmBW = None
                    measure.algorithmBCS = None


        if 'favorite' in request.form:
            favorite_str = request.form.get('favorite', 'false')
            new_favorite = favorite_str.lower() == 'true'
            if measure.favorite != new_favorite:
                measure.favorite = new_favorite
                updated = True


        if recalculate_algo:
            try:
                logger.info(f"Recalculating algorithm results for measure {measure_id}")
                results = forward_coordinates(measure.coordinates) # measure.coordinates is a list of dicts
                if results.get('error'):
                    logger.error(f"Coordinate processing failed during update for measure {measure_id}: {results['error']}")
                    # Similar to add_measure, decide on error handling.
                    # For now, log and potentially clear/keep old values.
                    measure.algorithmBW = results.get('algorithmBW') # Update BW if available
                    measure.algorithmBCS = None # Clear BCS if calculation failed
                else:
                    measure.algorithmBW = results.get('algorithmBW')
                    measure.algorithmBCS = results.get('algorithmBCS')
                updated = True # Mark as updated if algo values changed or were recalculated
            except Exception as e:
                logger.error(f"Failed to re-process coordinates for measure {measure_id}: {e}")


        picture_file = request.files.get('picture')
        remove_flag = request.form.get('remove_picture', 'false').lower() == 'true'
        old_picture_filename = measure.picturePath

        if picture_file:
            try:
                new_filename = _save_measure_image_from_filestorage(picture_file, measure.id, measure.horseId)
                measure.picturePath = new_filename
                updated = True

                _delete_measure_image(old_picture_filename)
            except ValueError as e:
                raise BadRequest(str(e))

        elif remove_flag:
            if old_picture_filename:
                if _delete_measure_image(old_picture_filename):
                    measure.picturePath = None
                    updated = True
                else:
                    logger.error(f"Failed to delete image file {old_picture_filename} during update for measure {measure_id}")


        if not updated:

            relevant_fields = ['horseId', 'date', 'veterinarianId', 'appointmentId',
                               'coordinates', 'userBW', 'userBCS', 'favorite', 'remove_picture']
            if any(field in request.form for field in relevant_fields) or 'picture' in request.files:
                 return jsonify({"message": "No changes detected in provided fields."}), 200
            else:
                 return jsonify({"message": "No relevant update fields provided."}), 400


        db.session.commit()
        logger.info(f"Measure {measure_id} updated.")

        return jsonify({
            'id': measure.id,
            'horseId': measure.horseId,
            'date': measure.date.isoformat(),
            'veterinarianId': measure.veterinarianId,
            'appointmentId': measure.appointmentId,
            'coordinates': measure.coordinates,
            'userBW': measure.userBW,
            'userBCS': measure.userBCS,
            'algorithmBW': measure.algorithmBW,
            'algorithmBCS': measure.algorithmBCS,
            'favorite': measure.favorite,
            'picturePath': _get_measure_image_url(measure.picturePath)
        }), 200

    except (NotFound, BadRequest, UnsupportedMediaType) as e:
         db.session.rollback()
         logger.warning(f"Client error updating measure {measure_id}: {e}")
         return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error updating measure {measure_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@measures_bp.route('/measure/<int:measure_id>', methods=['DELETE'])
@jwt_required()
def delete_measure(measure_id):
    """Deletes a measure and its image using the ID from the URL."""
    try:
        measure = Measure.query.get_or_404(measure_id, description=f"Measure with id {measure_id} not found.")
        picture_filename_to_delete = measure.picturePath

        db.session.delete(measure)
        db.session.commit()
        logger.info(f"Measure {measure_id} deleted from database.")


        _delete_measure_image(picture_filename_to_delete)

        return jsonify({"message": "Measure deleted successfully"}), 200

    except NotFound as e:
         db.session.rollback()
         logger.warning(f"Client error deleting measure {measure_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error deleting measure {measure_id}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500
