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
            phone_number=data.get('phoneNumber'),
            phone_country_code=data.get('phoneCountryCode')
        )
        db.session.add(client)
        db.session.commit()
        
        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phone_number,
            "phoneCountryCode": client.phone_country_code
        }), 201

    except Exception as e:
        return jsonify({"Error": str(e)}), 500



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