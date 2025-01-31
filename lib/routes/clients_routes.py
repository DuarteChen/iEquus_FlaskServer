from flask import Blueprint, request, jsonify
from lib.models import Client, db
import phonenumbers
from email_validator import validate_email, EmailNotValidError

clients_bp = Blueprint('clients', __name__)


@clients_bp.route('/clients', methods=['POST'])
def add_client():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        phone_country_code = data.get('phone_country_code')
        
        if not name:
            return jsonify({"error": "Client name is required"}), 400
        
        if phone_number and not phone_country_code:
            return jsonify({"error": "Phone number and country code are required"}), 400
        
        if phone_number:
            try:
                full_number = phonenumbers.parse(phone_number, phone_country_code)
                if not phonenumbers.is_valid_number(full_number):
                    return jsonify({"error": "Invalid phone number"}), 400
            except phonenumbers.phonenumberutil.NumberParseException:
                return jsonify({"error": "Invalid phone number format"}), 400
        
        if email:
            # Validate the email using email-validator
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return jsonify({"error": f"Invalid email format: {str(e)}"}), 400
        
        # Store the client in the database
        client = Client(
            name=name,
            phone_number=phone_number,
            phone_country_code=phone_country_code,
            email=email
        )
        db.session.add(client)
        db.session.commit()

        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "phoneNumber": client.phone_number,
            "phoneCountryCode": client.phone_country_code,
            "email": client.email
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@clients_bp.route('/clients', methods=['GET'])
def get_clients():
    try:
        clients = Client.query.all() #cria-se uma lista de objetos da classe Client

        clients_list = [{"idClient": client.id, "name": client.name, "email": client.email,
                         "phoneNumber": client.phone_number, "phoneCountryCode": client.phone_country_code}
                        for client in clients]
        return jsonify(clients_list), 200
        

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@clients_bp.route('/client/<int:id>', methods=['GET'])
def get_clientById(id):
    try:
        # Retrieve the client by ID
        client = Client.query.get(id)
        
        if not client:
            return jsonify({"error": "Horse not found"}), 404
            
        #TODO - retrieve more info as needed, as appointmens, or list of horses and other info
        return jsonify({
                "idClient": client.id,
                "name": client.name,
                "email": client.email,
                "phoneNumber": client.phone_number,
                "phoneCountryCode": client.phone_country_code
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@clients_bp.route('/clients/<int:id>', methods=['PUT'])
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


        if 'phone_number' in data:
            phone_number = data.get('phone_number')
        if 'phone_country_code' in data:
            phone_country_code = data.get('phone_country_code')
        else:
            phone_country_code = client.phone_country_code
        
        try:
            full_number = phonenumbers.parse(phone_number, phone_country_code)
            if not phonenumbers.is_valid_number(full_number):
                return jsonify({"error": "Invalid phone number"}), 400
        except phonenumbers.phonenumberutil.NumberParseException:
            return jsonify({"error": "Invalid phone number format"}), 400
        
        client.phoneNumber = phone_number
        client.phoneNumber = phone_country_code


        
        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phone_number,
            "phoneCountryCode": client.phone_country_code
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