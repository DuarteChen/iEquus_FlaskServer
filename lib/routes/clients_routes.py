from flask import Blueprint, request, jsonify, url_for
from lib.models import Client, ClientHorse, Horse, db
import phonenumbers
from email_validator import validate_email, EmailNotValidError

clients_bp = Blueprint('clients', __name__)


@clients_bp.route('/clients', methods=['POST'])
def add_client():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phoneNumber = data.get('phoneNumber')
        phoneCountryCode = data.get('phoneCountryCode')
        
        if not name:
            return jsonify({"error": "Client name is required"}), 400
        
        if phoneNumber and not phoneCountryCode:
            return jsonify({"error": "Phone number and country code are required"}), 400
        
        if phoneNumber:
            try:
                full_number = phonenumbers.parse(phoneNumber, phoneCountryCode)
                if not phonenumbers.is_valid_number(full_number):
                    return jsonify({"error": "Invalid phone number"}), 400
            except phonenumbers.phonenumberutil.NumberParseException:
                return jsonify({"error": "Invalid phone number format"}), 400
        
        if email:
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return jsonify({"error": f"Invalid email format: {str(e)}"}), 400
        
        client = Client(
            name=name,
            phoneNumber=phoneNumber,
            phoneCountryCode=phoneCountryCode,
            email=email
        )
        db.session.add(client)
        db.session.commit()

        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode,
            "email": client.email
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@clients_bp.route('/clients', methods=['GET'])
def get_clients():
    try:
        clients = Client.query.all() #cria-se uma lista de objetos da classe Client

        clients_list = [{"idClient": client.id, "name": client.name, "email": client.email,
                         "phoneNumber": client.phoneNumber, "phoneCountryCode": client.phoneCountryCode}
                        for client in clients]
        return jsonify(clients_list), 200
        

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@clients_bp.route('/client/<int:id>', methods=['GET'])
def get_clientById(id):
    try:

        client = Client.query.get(id)
        
        if not client:
            return jsonify({"error": "Client not found"}), 404
            
        #TODO - retrieve more info as needed, as appointmens, or list of horses and other info
        return jsonify({
                "idClient": client.id,
                "name": client.name,
                "email": client.email,
                "phoneNumber": client.phoneNumber,
                "phoneCountryCode": client.phoneCountryCode
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@clients_bp.route('/client/<int:id>', methods=['PUT'])
def update_client(id):
    try:
        # Retrieve the client by ID
        client = Client.query.get(id)

        if not client:
            return jsonify({"error": "Client not found"}), 404

        # Get the new data from the request
        data = request.get_json()

        # Update the fields, if they are provided in the request
        if 'name' in data:
            client.name = data['name']

        if 'email' in data:
            email = data.get('email')

            # Validate the email using email-validator
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return jsonify({"error": f"Invalid email format: {str(e)}"}), 400

            client.email = email


        if 'phoneNumber' in data:
            phoneNumber = data.get('phoneNumber')
        if 'phoneCountryCode' in data:
            phoneCountryCode = data.get('phoneCountryCode')
        else:
            phoneCountryCode = client.phoneCountryCode
        
        try:
            full_number = phonenumbers.parse(phoneNumber, phoneCountryCode)
            if not phonenumbers.is_valid_number(full_number):
                return jsonify({"error": "Invalid phone number"}), 400
        except phonenumbers.phonenumberutil.NumberParseException:
            return jsonify({"error": "Invalid phone number format"}), 400
        
        client.phoneNumber = phoneNumber
        client.phoneNumber = phoneCountryCode


        
        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@clients_bp.route('/clients/<int:id>', methods = ['DELETE'])
def delete_client(id):
    try:
        client = Client.query.get(id)
        if not client:
            return jsonify({"error": "Client not found"}), 404
        
        db.session.delete(client)
        db.session.commit()

        return jsonify({"message": "Client deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@clients_bp.route('/client/<int:client_id>/horses/<int:horseId>', methods=['POST'])
def add_horse_to_client(client_id, horseId):
    try:

        client = Client.query.get(client_id)
        if not client:
            return jsonify({"error": "Client not found"}), 404


        horse = Horse.query.get(horseId)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404


        existing_relation = ClientsHasHorses.query.filter_by(client_id=client_id, horseId=horseId).first()
        if existing_relation:
            return jsonify({"message": "Client already associated with this horse"}), 400


        is_owner = request.json.get("isClientHorseOwner", False)  # Default is False
        client_horse_relation = ClientsHasHorses(client_id=client_id, horseId=horseId, is_client_horse_owner=is_owner)

        db.session.add(client_horse_relation)
        db.session.commit()

        return jsonify({"message": "Horse successfully associated with client"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@clients_bp.route('/client/<int:client_id>/horses', methods=['GET'])
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
    
@clients_bp.route('/client/<int:client_id>/horses/<int:horseId>', methods=['DELETE'])
def remove_horse_from_client(client_id, horseId):
    try:
        relation = ClientsHasHorses.query.filter_by(client_id=client_id, horseId=horseId).first()
        if not relation:
            return jsonify({"error": "Client is not associated with this horse"}), 404

        db.session.delete(relation)
        db.session.commit()

        return jsonify({"message": "Horse successfully removed from client"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500