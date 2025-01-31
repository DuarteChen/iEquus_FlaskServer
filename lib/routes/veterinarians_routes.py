from email_validator import EmailNotValidError, ValidatedEmail
from flask import Blueprint, request, jsonify
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from lib.models import Veterinarian, db

veterinarians_bp = Blueprint('veterinarians', __name__)

@veterinarians_bp.route('/veterinarian', methods=['POST'])
def add_veterinarian():
    try:
        data = request.get_json()
        name = data.get('name')
        id_cedula_profissional = data.get('id_cedula_profissional')
        email = data.get('email')
        phone_number = data.get('phone_number')
        phone_country_code = data.get('phone_country_code')

        if not name or not id_cedula_profissional:
            return jsonify({"error": "Veterinarian name and idCedulaProfissional are required"}), 400
        
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

        
        veterinarian = Veterinarian(
            name=name,
            email=email,
            phone_number=phone_number,
            phone_country_code=phone_country_code,
            id_cedula_profissional=id_cedula_profissional
        )
        db.session.add(veterinarian)
        db.session.commit()
        
        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phone_number,
            "phoneCountryCode": veterinarian.phone_country_code,
            "idCedulaProfissional": veterinarian.id_cedula_profissional
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@veterinarians_bp.route('/veterinarians', methods=['GET'])
def get_veterinarians():
    try:
        veterinarians = Veterinarian.query.all()
        veterinarians_list = [{
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phone_number,
            "phoneCountryCode": veterinarian.phone_country_code,
            "idCedulaProfissional": veterinarian.id_cedula_profissional
        } for veterinarian in veterinarians]
        
        return jsonify(veterinarians_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@veterinarians_bp.route('/veterinarian/<int:id>', methods=['GET'])
def get_veterinarianById(id):
    try:
        # Retrieve the veterinarian by ID
        veterinarian = Veterinarian.query.get(id)
        
        if not veterinarian:
            return jsonify({"error": "Veterinarian not found"}), 404
            
        #TODO - retrieve more info as needed, as appointmens, or list of horses and other info
        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phone_number,
            "phoneCountryCode": veterinarian.phone_country_code,
            "idCedulaProfissional": veterinarian.id_cedula_profissional
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@veterinarians_bp.route('/veterinarian/<int:id>', methods=['PUT'])
def update_veterinarian(id):
    try:
        # Retrieve the client by ID
        veterinarian = Veterinarian.query.get(id)

        if not veterinarian:
            return jsonify({"error": "Client not found"}), 404

        # Get the new data from the request
        data = request.get_json()

        # Update the fields, if they are provided in the request
        if 'name' in data:
            veterinarian.name = data['name']

        if 'email' in data:
            email = data.get('email')

            # Validate the email using email-validator
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return jsonify({"error": f"Invalid email format: {str(e)}"}), 400

            veterinarian.email = email


        if 'phone_number' in data:
            phone_number = data.get('phone_number')
        if 'phone_country_code' in data:
            phone_country_code = data.get('phone_country_code')
        else:
            phone_country_code = veterinarian.phone_country_code
        
        try:
            full_number = phonenumbers.parse(phone_number, phone_country_code)
            if not phonenumbers.is_valid_number(full_number):
                return jsonify({"error": "Invalid phone number"}), 400
        except phonenumbers.phonenumberutil.NumberParseException:
            return jsonify({"error": "Invalid phone number format"}), 400
        
        veterinarian.phoneNumber = phone_number
        veterinarian.phoneNumber = phone_country_code


        if 'id_cedula_profissional' in data:
            veterinarian.id_cedula_profissional = data.get('id_cedula_profissional')

        
        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phone_number,
            "phoneCountryCode": veterinarian.phone_country_code,
            "idCedulaProfissional": veterinarian.id_cedula_profissional
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@veterinarians_bp.route('/veterinarian/<int:id>', methods = ['DELETE'])
def delete_veterinarian(id):
    try:
        veterinarian = Veterinarian.query.get(id)
        if not veterinarian:
            return jsonify({"error": "Veterinarian not found"}), 404
        
        db.session.delete(veterinarian)
        db.session.commit()

        return jsonify({"message": "Veterinarian deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500