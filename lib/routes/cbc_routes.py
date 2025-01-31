from flask import Blueprint, request, jsonify
from lib.models import CBC, db

cbc_bp = Blueprint('cbc', __name__)

@cbc_bp.route('/cbc', methods=['POST'])
def add_cbc():
    try:
        data = request.get_json()
        if 'vetAppointment' not in data or 'path' not in data or 'date' not in data:
            return jsonify({"error": "vetAppointment, path, and date are required"}), 400
        
        cbc = CBC(
            vet_appointment=data['vetAppointment'],
            path=data['path'],
            date=data['date']
        )
        db.session.add(cbc)
        db.session.commit()
        
        return jsonify({
            "idCBC": cbc.id,
            "vetAppointment": cbc.vet_appointment,
            "path": cbc.path,
            "date": cbc.date
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cbc_bp.route('/cbc', methods=['GET'])
def get_cbc():
    try:
        cbcs = CBC.query.all()
        cbc_list = [{
            "idCBC": c.id,
            "vetAppointment": c.vet_appointment,
            "path": c.path,
            "date": c.date
        } for c in cbcs]
        
        return jsonify(cbc_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500