import os
from datetime import datetime
from uuid import uuid4
from flask import Blueprint, request, jsonify, url_for
from werkzeug.utils import secure_filename
from lib.models import Horse, db
from PIL import Image


project_dir = os.getcwd()  # This will give you the current working directory

# Define the paths for profile pictures and limb pictures
profile_PicturesFolder = os.path.join(project_dir, 'lib','static', 'images', 'horse_profile')
limbs_PicturesFolder = os.path.join(project_dir, 'lib', 'static', 'images', 'horse_limbs')

# Make sure the directories exist; if not, create them
for folder in [profile_PicturesFolder, limbs_PicturesFolder]:
    if not os.path.exists(folder):
        os.makedirs(folder)  # Create the directory if it doesn't exist


horses_bp = Blueprint('horses', __name__)

@horses_bp.route('/horses', methods=['GET'])
def get_horses():
    try:
        horses = Horse.query.all()
        horses_list = [{
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": url_for('static', filename=f'images/horse_profile/{horse.profile_picture_path}', _external=True) if horse.profile_picture_path else None,
            "birthDate": horse.birth_date,
            "pictureRightFrontPath": url_for('static', filename=f'images/horse_limbs/{horse.picture_right_front_path}', _external=True) if horse.picture_right_front_path else None,
            "pictureLeftFrontPath": url_for('static', filename=f'images/horse_limbs/{horse.picture_left_front_path}', _external=True) if horse.picture_left_front_path else None,
            "pictureRightHindPath": url_for('static', filename=f'images/horse_limbs/{horse.picture_right_hind_path}', _external=True) if horse.picture_right_hind_path else None,
            "pictureLeftHindPath": url_for('static', filename=f'images/horse_limbs/{horse.picture_left_hind_path}', _external=True) if horse.picture_left_hind_path else None
        } for horse in horses]
        
        return jsonify(horses_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@horses_bp.route('/horse/<int:id>', methods=['GET'])
def get_horseById(id):

    try:
        # Retrieve the horse by ID
        horse = Horse.query.get(id)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404

        #TODO - retrieve more info as needed, as appointmens and other info
        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": horse.profile_picture_path,
            "birthDate": horse.birth_date,
            "pictureRightFrontPath": horse.picture_right_front_path,
            "pictureLeftFrontPath": horse.picture_left_front_path,
            "pictureRightHindPath": horse.picture_right_hind_path,
            "pictureLeftHindPath": horse.picture_left_hind_path
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@horses_bp.route('/horses', methods=['POST'])
def add_horse():
    try:
        
        birth_date_str = request.form.get('birthDate') #TODO - Pode ser removida esta linha, depois de ligar com o flutter
        expected_format = "%Y-%m-%d"
        try:
            birth_date = datetime.strptime(birth_date_str, expected_format)
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400



        name = request.form.get('name')
        if not name:
            return jsonify({"error": "Horse name is required"}), 400
        
        # Create a new Horse record
        horse = Horse(
            name=name,
            profile_picture_path=None,
            birth_date=birth_date,
            picture_right_front_path=None,
            picture_left_front_path=None,
            picture_right_hind_path=None,
            picture_left_hind_path=None
        )

        
        db.session.add(horse)
        db.session.commit()


        # Handle uploaded photos if any
        if 'photo' in request.files:
            # Handle profile picture
            file = request.files['photo']
            filename = secure_filename(file.filename)  # Secure the filename
            image = Image.open(file)
            
            # Generate a unique file name using UUID
            profile_picture_filename = f"{horse.id}_profile_{uuid4()}.webp"
            profile_picture_path = os.path.join(profile_PicturesFolder, profile_picture_filename)

            # Save the image in WebP format
            image.save(profile_picture_path, "WEBP", quality=100)

            # Update the horse record with the profile picture path
            horse.profile_picture_path = profile_picture_filename


        # Handle other possible images (front-right, front-left, hind-right, hind-left)
        if 'pictureRightFront' in request.files:
            file = request.files['pictureRightFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_front_filename = f"{horse.id}_right_front_{uuid4()}.webp"
            picture_right_front_path = os.path.join(limbs_PicturesFolder, picture_right_front_filename)
            image.save(picture_right_front_path, "WEBP", quality=100)
            horse.picture_right_front_path = picture_right_front_filename
        
        if 'pictureLeftFront' in request.files:
            file = request.files['pictureLeftFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_front_filename = f"{horse.id}_left_front_{uuid4()}.webp"
            picture_left_front_path = os.path.join(limbs_PicturesFolder, picture_left_front_filename)
            image.save(picture_left_front_path, "WEBP", quality=100)
            horse.picture_left_front_path = picture_left_front_filename
        
        if 'pictureRightHind' in request.files:
            file = request.files['pictureRightHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_hind_filename = f"{horse.id}_right_hind_{uuid4()}.webp"
            picture_right_hind_path = os.path.join(limbs_PicturesFolder, picture_right_hind_filename)
            image.save(picture_right_hind_path, "WEBP", quality=100)
            horse.picture_right_hind_path = picture_right_hind_filename
        
        if 'pictureLeftHind' in request.files:
            file = request.files['pictureLeftHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_hind_filename = f"{horse.id}_left_hind_{uuid4()}.webp"
            picture_left_hind_path = os.path.join(limbs_PicturesFolder, picture_left_hind_filename)
            image.save(picture_left_hind_path, "WEBP", quality=100)
            horse.picture_left_hind_path = picture_left_hind_filename
        
        db.session.commit()


        # Return the created horse with the file paths in the response
        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": horse.profile_picture_path,
            "birthDate": horse.birth_date,
            "pictureRightFrontPath": horse.picture_right_front_path,
            "pictureLeftFrontPath": horse.picture_left_front_path,
            "pictureRightHindPath": horse.picture_right_hind_path,
            "pictureLeftHindPath": horse.picture_left_hind_path
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@horses_bp.route('/horses/<int:id>', methods=['PUT'])
def update_horse(id):
    try:
        # Retrieve the horse by ID
        horse = Horse.query.get(id)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404

        # Optional: Check if the name was provided and update it
        name = request.form.get('name')
        if name:
            horse.name = name

        # Optional: Check if the birth date was provided and update it
        birth_date_str = request.form.get('birthDate')
        if birth_date_str:
            try:
                # Parse and validate the date format (if provided)
                expected_format = "%Y-%m-%d"
                birth_date = datetime.strptime(birth_date_str, expected_format)
                horse.birth_date = birth_date
            except ValueError:
                return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

        # Handle profile picture (if uploaded)
        if 'photo' in request.files:
            file = request.files['photo']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            
            # Generate a unique file name using UUID
            profile_picture_filename = f"{horse.id}_profile_{uuid4()}.webp"
            profile_picture_path = os.path.join(profile_PicturesFolder, profile_picture_filename)

            # Save the image in WebP format
            image.save(profile_picture_path, "WEBP", quality=100)

            # Update the horse record with the new profile picture path
            horse.profile_picture_path = profile_picture_filename

        # Handle limb pictures (if uploaded)
        if 'pictureRightFront' in request.files:
            file = request.files['pictureRightFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_front_filename = f"{horse.id}_right_front_{uuid4()}.webp"
            picture_right_front_path = os.path.join(limbs_PicturesFolder, picture_right_front_filename)
            image.save(picture_right_front_path, "WEBP", quality=100)
            horse.picture_right_front_path = picture_right_front_filename
        
        if 'pictureLeftFront' in request.files:
            file = request.files['pictureLeftFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_front_filename = f"{horse.id}_left_front_{uuid4()}.webp"
            picture_left_front_path = os.path.join(limbs_PicturesFolder, picture_left_front_filename)
            image.save(picture_left_front_path, "WEBP", quality=100)
            horse.picture_left_front_path = picture_left_front_filename
        
        if 'pictureRightHind' in request.files:
            file = request.files['pictureRightHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_hind_filename = f"{horse.id}_right_hind_{uuid4()}.webp"
            picture_right_hind_path = os.path.join(limbs_PicturesFolder, picture_right_hind_filename)
            image.save(picture_right_hind_path, "WEBP", quality=100)
            horse.picture_right_hind_path = picture_right_hind_filename
        
        if 'pictureLeftHind' in request.files:
            file = request.files['pictureLeftHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_hind_filename = f"{horse.id}_left_hind_{uuid4()}.webp"
            picture_left_hind_path = os.path.join(limbs_PicturesFolder, picture_left_hind_filename)
            image.save(picture_left_hind_path, "WEBP", quality=100)
            horse.picture_left_hind_path = picture_left_hind_filename
        
        db.session.commit()

        # Return the updated horse information
        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": horse.profile_picture_path,
            "birthDate": horse.birth_date,
            "pictureRightFrontPath": horse.picture_right_front_path,
            "pictureLeftFrontPath": horse.picture_left_front_path,
            "pictureRightHindPath": horse.picture_right_hind_path,
            "pictureLeftHindPath": horse.picture_left_hind_path
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@horses_bp.route('/horses/<int:id>', methods=['DELETE'])
def delete_horse(id):
    try:
        # Retrieve the horse by ID
        horse = Horse.query.get(id)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404

        # Delete associated images if they exist
        image_paths = [
            os.path.join(profile_PicturesFolder, horse.profile_picture_path) if horse.profile_picture_path else None,
            os.path.join(limbs_PicturesFolder, horse.picture_right_front_path) if horse.picture_right_front_path else None,
            os.path.join(limbs_PicturesFolder, horse.picture_left_front_path) if horse.picture_left_front_path else None,
            os.path.join(limbs_PicturesFolder, horse.picture_right_hind_path) if horse.picture_right_hind_path else None,
            os.path.join(limbs_PicturesFolder, horse.picture_left_hind_path) if horse.picture_left_hind_path else None
        ]

        # Remove images from the file system
        for path in image_paths:
            if path and os.path.exists(path):
                os.remove(path)

        # Delete the horse from the database
        db.session.delete(horse)
        db.session.commit()

        return jsonify({"message": "Horse deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500