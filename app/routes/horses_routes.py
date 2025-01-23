from flask import Blueprint, request, jsonify, url_for
from app.models import Horse, db

horses_bp = Blueprint('horses', __name__)

@horses_bp.route('/horses', methods=['POST'])
def add_horse():
    try:
        data = request.get_json()
        if 'name' not in data:
            return jsonify({"error": "Horse name is required"}), 400
        
        horse = Horse(
            name=data['name'],
            profile_picture_path=data.get('profilePicturePath'),
            birth_date=data.get('birthDate'),
            picture_right_front_path=data.get('pictureRightFrontPath'),
            picture_left_front_path=data.get('pictureLeftFrontPath'),
            picture_right_hind_path=data.get('pictureRightHindPath'),
            picture_left_hind_path=data.get('pictureLeftHindPath')
        )
        db.session.add(horse)
        db.session.commit()
        
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


@horses_bp.route('/horses', methods=['GET'])
def get_horses():
    try:
        horses = Horse.query.all()
        horses_list = [{
            "idHorse": horse.id,
            "name": horse.name,
            "profilePicturePath": url_for('static', filename=f'images/horse_profile/{horse.profile_picture_path}', _external=True) if horse.profile_picture_path else None,
            "birthDate": horse.birth_date,
            "pictureRightFrontPath": url_for('static', filename=f'images/{horse.picture_right_front_path}', _external=True) if horse.picture_right_front_path else None,
            "pictureLeftFrontPath": url_for('static', filename=f'images/{horse.picture_left_front_path}', _external=True) if horse.picture_left_front_path else None,
            "pictureRightHindPath": url_for('static', filename=f'images/{horse.picture_right_hind_path}', _external=True) if horse.picture_right_hind_path else None,
            "pictureLeftHindPath": url_for('static', filename=f'images/{horse.picture_left_hind_path}', _external=True) if horse.picture_left_hind_path else None
        } for horse in horses]
        
        return jsonify(horses_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
