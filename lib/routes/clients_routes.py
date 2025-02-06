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
    
@clients_bp.route('/client/<int:clientId_arg>/horse/<int:horseId_arg>', methods=['POST'])
def add_horse_to_client(clientId_arg, horseId_arg):
    try:
        # Get the client from the database
        client = Client.query.get(clientId_arg)
        if not client:
            return jsonify({"error": "Client not found"}), 404

        # Get the horse from the database
        horse = Horse.query.get(horseId_arg)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404

        # Check if the relation already exists
        existing_relation = ClientHorse.query.filter_by(clientId=clientId_arg, horseId=horseId_arg).first()
        if existing_relation:
            return jsonify({"message": "Client already associated with this horse"}), 400

        # Get 'isClientHorseOwner' from the request's JSON payload
        isClientHorseOwner = request.json.get('isClientHorseOwner', False)  # Default to False if not provided

        # Create the association in the ClientHorse table
        client_horse_relation = ClientHorse(clientId=clientId_arg, horseId=horseId_arg, isClientHorseOwner=isClientHorseOwner)

        # Add to the session and commit
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
        
        horses_list = []
        for horse in client.horses:
            # Query the ClientHorse table to get the relation for each horse
            relation = ClientHorse.query.filter_by(clientId=client_id, horseId=horse.id).first()

            # Only add to the list if the relation exists
            if relation:
                horses_list.append({
                    "idHorse": horse.id,
                    "name": horse.name,
                    "profilePicturePath": url_for('static', filename=f'images/horse_profile/{horse.profilePicturePath}', _external=True) if horse.profilePicturePath else None,
                    "birthDate": horse.birthDate,
                    "isOwner": relation.isClientHorseOwner
                })

        return jsonify(horses_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@clients_bp.route('/client/<int:clientId_arg>/horse/<int:horseId_arg>', methods=['PUT'])
def update_horse_to_client(clientId_arg, horseId_arg):
    try:
        # Get the client from the database
        client = Client.query.get(clientId_arg)
        if not client:
            return jsonify({"error": "Client not found"}), 404

        # Get the horse from the database
        horse = Horse.query.get(horseId_arg)
        if not horse:
            return jsonify({"error": "Horse not found"}), 404

        # Check if the relation exists
        existing_relation = ClientHorse.query.filter_by(clientId=clientId_arg, horseId=horseId_arg).first()
        if not existing_relation:
            return jsonify({"message": "Client is not associated with this horse"}), 400

        # Get the updated 'isClientHorseOwner' from the request's JSON payload
        isClientHorseOwner = request.json.get('isClientHorseOwner')
        if isClientHorseOwner is None:  # Make sure the value is provided
            return jsonify({"message": "Value 'isClientHorseOwner' needed to proceed"}), 400

        # Update the existing relation's 'isClientHorseOwner' value
        existing_relation.isClientHorseOwner = isClientHorseOwner

        # Commit the update to the database
        db.session.commit()

        return jsonify({"message": "Horse's relation with client successfully updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    
@clients_bp.route('/client/<int:client_id>/horses/<int:horseId>', methods=['DELETE'])
def remove_horse_from_client(client_id, horseId):
    try:
        relation = ClientHorse.query.filter_by(clientId=client_id, horseId=horseId).first()
        if not relation:
            return jsonify({"error": "Client is not associated with this horse"}), 404

        db.session.delete(relation)
        db.session.commit()

        return jsonify({"message": "Horse successfully removed from client"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500