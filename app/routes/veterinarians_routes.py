from flask import Blueprint, request, jsonify
from app.models import Veterinarian, db

veterinarians_bp = Blueprint('veterinarians', __name__)

@veterinarians_bp.route('/veterinarians', methods=['POST'])
def add_veterinarian():
    try:
        data = request.get_json()
        if 'name' not in data or 'idCedulaProfissional' not in data:
            return jsonify({"error": "Veterinarian name and idCedulaProfissional are required"}), 400
        
        veterinarian = Veterinarian(
            name=data['name'],
            email=data.get('email'),
            phone_number=data.get('phoneNumber'),
            phone_country_code=data.get('phoneCountryCode'),
            password=data.get('password'),
            id_cedula_profissional=data['idCedulaProfissional']
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
            "idVeterinary": vet.id,
            "name": vet.name,
            "email": vet.email,
            "phoneNumber": vet.phone_number,
            "phoneCountryCode": vet.phone_country_code,
            "idCedulaProfissional": vet.id_cedula_profissional
        } for vet in veterinarians]
        
        return jsonify(veterinarians_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500