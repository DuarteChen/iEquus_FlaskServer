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
            "profilePicturePath": url_for('static', filename=f'images/horse_profile/{horse.profilePicturePath}', _external=True) if horse.profilePicturePath else None,
            "birthDate": horse.birthDate,
            "pictureRightFrontPath": url_for('static', filename=f'images/horse_limbs/{horse.pictureRightFrontPath}', _external=True) if horse.pictureRightFrontPath else None,
            "pictureLeftFrontPath": url_for('static', filename=f'images/horse_limbs/{horse.pictureLeftFrontPath}', _external=True) if horse.pictureLeftFrontPath else None,
            "pictureRightHindPath": url_for('static', filename=f'images/horse_limbs/{horse.pictureRightHindPath}', _external=True) if horse.pictureRightHindPath else None,
            "pictureLeftHindPath": url_for('static', filename=f'images/horse_limbs/{horse.pictureLeftHindPath}', _external=True) if horse.pictureLeftHindPath else None
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
            "profilePicturePath": horse.profilePicturePath,
            "birthDate": horse.birthDate,
            "pictureRightFrontPath": horse.pictureRightFrontPath,
            "pictureLeftFrontPath": horse.pictureLeftFrontPath,
            "pictureRightHindPath": horse.pictureRightHindPath,
            "pictureLeftHindPath": horse.pictureLeftHindPath
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@horses_bp.route('/horses', methods=['POST'])
def add_horse():
    try:
        
        birth_date_str = request.form.get('birthDate') #TODO - Pode ser removida esta linha, depois de ligar com o flutter
        expected_format = "%Y-%m-%d"
        try:
            birthDate = datetime.strptime(birth_date_str, expected_format)
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400



        name = request.form.get('name')
        if not name:
            return jsonify({"error": "Horse name is required"}), 400
        
        # Create a new Horse record
        horse = Horse(
            name=name,
            profilePicturePath=None,
            birthDate=birthDate,
            pictureRightFrontPath=None,
            pictureLeftFrontPath=None,
            pictureRightHindPath=None,
            pictureLeftHindPath=None
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
            profilePicturePath = os.path.join(profile_PicturesFolder, profile_picture_filename)

            # Save the image in WebP format
            image.save(profilePicturePath, "WEBP", quality=100)

            # Update the horse record with the profile picture path
            horse.profilePicturePath = profile_picture_filename


        # Handle other possible images (front-right, front-left, hind-right, hind-left)
        if 'pictureRightFront' in request.files:
            file = request.files['pictureRightFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_front_filename = f"{horse.id}_right_front_{uuid4()}.webp"
            pictureRightFrontPath = os.path.join(limbs_PicturesFolder, picture_right_front_filename)
            image.save(pictureRightFrontPath, "WEBP", quality=100)
            horse.pictureRightFrontPath = picture_right_front_filename
        
        if 'pictureLeftFront' in request.files:
            file = request.files['pictureLeftFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_front_filename = f"{horse.id}_left_front_{uuid4()}.webp"
            pictureLeftFrontPath = os.path.join(limbs_PicturesFolder, picture_left_front_filename)
            image.save(pictureLeftFrontPath, "WEBP", quality=100)
            horse.pictureLeftFrontPath = picture_left_front_filename
        
        if 'pictureRightHind' in request.files:
            file = request.files['pictureRightHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_hind_filename = f"{horse.id}_right_hind_{uuid4()}.webp"
            pictureRightHindPath = os.path.join(limbs_PicturesFolder, picture_right_hind_filename)
            image.save(pictureRightHindPath, "WEBP", quality=100)
            horse.pictureRightHindPath = picture_right_hind_filename
        
        if 'pictureLeftHind' in request.files:
            file = request.files['pictureLeftHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_hind_filename = f"{horse.id}_left_hind_{uuid4()}.webp"
            pictureLeftHindPath = os.path.join(limbs_PicturesFolder, picture_left_hind_filename)
            image.save(pictureLeftHindPath, "WEBP", quality=100)
            horse.pictureLeftHindPath = picture_left_hind_filename
        
        db.session.commit()


        # Return the created horse with the file paths in the response
        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": horse.profilePicturePath,
            "birthDate": horse.birthDate,
            "pictureRightFrontPath": horse.pictureRightFrontPath,
            "pictureLeftFrontPath": horse.pictureLeftFrontPath,
            "pictureRightHindPath": horse.pictureRightHindPath,
            "pictureLeftHindPath": horse.pictureLeftHindPath
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
                birthDate = datetime.strptime(birth_date_str, expected_format)
                horse.birthDate = birthDate
            except ValueError:
                return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

        # Handle profile picture (if uploaded)
        if 'photo' in request.files:
            file = request.files['photo']
            filename = secure_filename(file.filename)
            image = Image.open(file)

            # Handle picture update
            # Check if there is an old picture to delete
            if horse.profilePicturePath and os.path.exists(horse.profilePicturePath):
                os.remove(horse.profilePicturePath)  # Delete the old picture
            
            # Generate a unique file name using UUID
            profile_picture_filename = f"{horse.id}_profile_{uuid4()}.webp"
            profilePicturePath = os.path.join(profile_PicturesFolder, profile_picture_filename)

            # Save the image in WebP format
            image.save(profilePicturePath, "WEBP", quality=100)

            # Update the horse record with the new profile picture path
            horse.profilePicturePath = profile_picture_filename

        # Handle limb pictures (if uploaded)
        if 'pictureRightFront' in request.files:

            # Handle picture update
            # Check if there is an old picture to delete
            if horse.pictureRightFrontPath and os.path.exists(horse.pictureRightFrontPath):
                os.remove(horse.pictureRightFrontPath)  # Delete the old picture

            file = request.files['pictureRightFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_front_filename = f"{horse.id}_right_front_{uuid4()}.webp"
            pictureRightFrontPath = os.path.join(limbs_PicturesFolder, picture_right_front_filename)
            image.save(pictureRightFrontPath, "WEBP", quality=100)
            horse.pictureRightFrontPath = picture_right_front_filename
        
        if 'pictureLeftFront' in request.files:
            # Handle picture update
            # Check if there is an old picture to delete
            if horse.pictureLeftFrontPath and os.path.exists(horse.pictureLeftFrontPath):
                os.remove(horse.pictureLeftFrontPath)  # Delete the old picture

            file = request.files['pictureLeftFront']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_front_filename = f"{horse.id}_left_front_{uuid4()}.webp"
            pictureLeftFrontPath = os.path.join(limbs_PicturesFolder, picture_left_front_filename)
            image.save(pictureLeftFrontPath, "WEBP", quality=100)
            horse.pictureLeftFrontPath = picture_left_front_filename
        
        if 'pictureRightHind' in request.files:
            # Handle picture update
            # Check if there is an old picture to delete
            if horse.pictureRightHindPath and os.path.exists(horse.pictureRightHindPath):
                os.remove(horse.pictureRightHindPath)  # Delete the old picture

            
            file = request.files['pictureRightHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_right_hind_filename = f"{horse.id}_right_hind_{uuid4()}.webp"
            pictureRightHindPath = os.path.join(limbs_PicturesFolder, picture_right_hind_filename)
            image.save(pictureRightHindPath, "WEBP", quality=100)
            horse.pictureRightHindPath = picture_right_hind_filename
        
        if 'pictureLeftHind' in request.files:
            # Handle picture update
            # Check if there is an old picture to delete
            if horse.pictureLeftHindPath and os.path.exists(horse.pictureLeftHindPath):
                os.remove(horse.pictureLeftHindPath)  # Delete the old picture

            file = request.files['pictureLeftHind']
            filename = secure_filename(file.filename)
            image = Image.open(file)
            picture_left_hind_filename = f"{horse.id}_left_hind_{uuid4()}.webp"
            pictureLeftHindPath = os.path.join(limbs_PicturesFolder, picture_left_hind_filename)
            image.save(pictureLeftHindPath, "WEBP", quality=100)
            horse.pictureLeftHindPath = picture_left_hind_filename
        
        db.session.commit()

        # Return the updated horse information
        return jsonify({
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": horse.profilePicturePath,
            "birthDate": horse.birthDate,
            "pictureRightFrontPath": horse.pictureRightFrontPath,
            "pictureLeftFrontPath": horse.pictureLeftFrontPath,
            "pictureRightHindPath": horse.pictureRightHindPath,
            "pictureLeftHindPath": horse.pictureLeftHindPath
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
            os.path.join(profile_PicturesFolder, horse.profilePicturePath) if horse.profilePicturePath else None,
            os.path.join(limbs_PicturesFolder, horse.pictureRightFrontPath) if horse.pictureRightFrontPath else None,
            os.path.join(limbs_PicturesFolder, horse.pictureLeftFrontPath) if horse.pictureLeftFrontPath else None,
            os.path.join(limbs_PicturesFolder, horse.pictureRightHindPath) if horse.pictureRightHindPath else None,
            os.path.join(limbs_PicturesFolder, horse.pictureLeftHindPath) if horse.pictureLeftHindPath else None
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