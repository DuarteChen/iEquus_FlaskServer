from flask import Blueprint, request, jsonify, url_for
from werkzeug.utils import secure_filename
from lib.models import Client, ClientsHasHorses, Horse, db

clients_horses_bp = Blueprint('clients_horses', __name__)

@clients_horses_bp.route('/client/<int:client_id>/horse/<int:horse_id>', methods=['POST'])
def add_horse_to_client(client_id, horse_id):
    try:
        # Check if client exists
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"error": "Client not found"}), 404

        # Check if horse exists
        horse = Horse.query.get(horse_id)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404

        # Check if the relationship already exists
        existing_relation = ClientsHasHorses.query.filter_by(client_id=client_id, horse_id=horse_id).first()
        if existing_relation:
            return jsonify({"message": "Client already associated with this horse"}), 400

        # Add horse to client
        client_horse_relation = ClientsHasHorses(client_id=client_id, horse_id=horse_id, is_client_horse_owner=True)

        db.session.add(client_horse_relation)
        db.session.commit()

        return jsonify({"message": "Horse successfully associated with client"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@clients_horses_bp.route('/client/<int:client_id>/horses', methods=['GET'])
def get_client_horses(client_id):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"error": "Client not found"}), 404

        horses_list = [{
            "idHorse": relation.horse.id,
            "name": relation.horse.name,
            "profilePicturePath": url_for('static', filename=f'images/horse_profile/{relation.horse.profile_picture_path}', _external=True) if relation.horse.profile_picture_path else None,
            "birthDate": relation.horse.birth_date,
            "isOwner": relation.is_client_horse_owner
        } for relation in client.horses]

        return jsonify(horses_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@clients_horses_bp.route('/client/<int:client_id>/horse/<int:horse_id>', methods=['DELETE'])
def remove_horse_from_client(client_id, horse_id):
    try:
        relation = ClientsHasHorses.query.filter_by(client_id=client_id, horse_id=horse_id).first()
        if not relation:
            return jsonify({"error": "Client is not associated with this horse"}), 404

        db.session.delete(relation)
        db.session.commit()

        return jsonify({"message": "Horse successfully removed from client"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500