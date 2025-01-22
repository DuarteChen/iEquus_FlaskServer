from flask import Blueprint, request, jsonify
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
            profilePicturePath=data.get('profilePicturePath'),
            birthDate=data.get('birthDate'),
            pictureRightFrontPath=data.get('pictureRightFrontPath'),
            pictureLeftFrontPath=data.get('pictureLeftFrontPath'),
            pictureRightHindPath=data.get('pictureRightHindPath'),
            pictureLeftHindPath=data.get('pictureLeftHindPath')
        )
        db.session.add(horse)
        db.session.commit()
        
        return jsonify({
            "idHorse": horse.idHorse,
            "name": horse.name,
            "profilePicturePath": horse.profilePicturePath,
            "birthDate": horse.birthDate,
            "pictureRightFrontPath": horse.pictureRightFrontPath,
            "pictureLeftFrontPath": horse.pictureLeftFrontPath,
            "pictureRightHindPath": horse.pictureRightHindPath,
            "pictureLeftHindPath": horse.pictureLeftHindPath,
            
        }), 201

    except Exception as e:
        return jsonify({"Error": str(e)}), 500



@horses_bp.route('/horses', methods=['GET'])
def get_horses():
    try:
        horses = Horse.query.all() #cria-se uma lista de objetos da classe Horse

        horses_list = [{
            "idHorse": horse.idHorse,
            "name": horse.name,
            "profilePicturePath": horse.profilePicturePath,
            "birthDate": horse.birthDate,
            "pictureRightFrontPath": horse.pictureRightFrontPath,
            "pictureLeftFrontPath": horse.pictureLeftFrontPath,
            "pictureRightHindPath": horse.pictureRightHindPath,
            "pictureLeftHindPath": horse.pictureLeftHindPath,
            
        } for horse in horses]
        return jsonify(horses_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500