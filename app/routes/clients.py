from flask import Blueprint, request, jsonify
from app.models import Client, db

clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/clients', methods=['POST'])
def add_client():
    try:
        data = request.get_json()
        if 'name' not in data:
            return jsonify({"error": "Client name is required"}), 400
        
        client = Client(
            name=data['name'],
            email=data.get('email'),
            phoneNumber=data.get('phoneNumber'),
            phoneCountryCode=data.get('phoneCountryCode')
        )
        db.session.add(client)
        db.session.commit()
        
        return jsonify({
            "idClient": client.idClient,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode
        }), 201

    except Exception as e:
        return jsonify({"Error": str(e)}), 500

@clients_bp.route('/clients', methods=['GET'])
def get_clients():
    try:
        clients = Client.query.all()
        clients_list = [{"idClient": client.idClient, "name": client.name, "email": client.email,
                         "phoneNumber": client.phoneNumber, "phoneCountryCode": client.phoneCountryCode}
                        for client in clients]
        return jsonify(clients_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500