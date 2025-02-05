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
        idCedulaProfissional = data.get('idCedulaProfissional')
        email = data.get('email')
        phoneNumber = data.get('phoneNumber')
        phoneCountryCode = data.get('phoneCountryCode')

        if not name or not idCedulaProfissional:
            return jsonify({"error": "Veterinarian name and idCedulaProfissional are required"}), 400
        
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

        
        veterinarian = Veterinarian(
            name=name,
            email=email,
            phoneNumber=phoneNumber,
            phoneCountryCode=phoneCountryCode,
            idCedulaProfissional=idCedulaProfissional
        )
        db.session.add(veterinarian)
        db.session.commit()
        
        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional
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
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional
        } for veterinarian in veterinarians]
        
        return jsonify(veterinarians_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@veterinarians_bp.route('/veterinarian/<int:id>', methods=['GET'])
def get_veterinarianById(id):
    try:
        veterinarian = Veterinarian.query.get(id)
        
        if not veterinarian:
            return jsonify({"error": "Veterinarian not found"}), 404
            
        #TODO - retrieve more info as needed, as appointmens, or list of horses and other info
        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@veterinarians_bp.route('/veterinarian/<int:id>', methods=['PUT'])
def update_veterinarian(id):
    try:

        veterinarian = Veterinarian.query.get(id)

        if not veterinarian:
            return jsonify({"error": "Client not found"}), 404


        data = request.get_json()


        if 'name' in data:
            veterinarian.name = data['name']

        if 'email' in data:
            email = data.get('email')

            
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return jsonify({"error": f"Invalid email format: {str(e)}"}), 400

            veterinarian.email = email


        if 'phoneNumber' in data:
            phoneNumber = data.get('phoneNumber')
        if 'phoneCountryCode' in data:
            phoneCountryCode = data.get('phoneCountryCode')
        else:
            phoneCountryCode = veterinarian.phoneCountryCode
        
        try:
            full_number = phonenumbers.parse(phoneNumber, phoneCountryCode)
            if not phonenumbers.is_valid_number(full_number):
                return jsonify({"error": "Invalid phone number"}), 400
        except phonenumbers.phonenumberutil.NumberParseException:
            return jsonify({"error": "Invalid phone number format"}), 400
        
        veterinarian.phoneNumber = phoneNumber
        veterinarian.phoneNumber = phoneCountryCode


        if 'idCedulaProfissional' in data:
            veterinarian.idCedulaProfissional = data.get('idCedulaProfissional')

        

        db.session.commit()

        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional
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