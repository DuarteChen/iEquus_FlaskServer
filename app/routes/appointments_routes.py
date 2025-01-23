from flask import Blueprint, request, jsonify
from app.models import Appointment, db

appointments_bp = Blueprint('appointments', __name__)

@appointments_bp.route('/appointments', methods=['POST'])
def add_appointment():
    try:
        data = request.get_json()
        if 'horseId' not in data or 'veterinaryID' not in data:
            return jsonify({"error": "horseId and veterinaryID are required"}), 400
        
        appointment = Appointment(
            horse_id=data['horseId'],
            veterinary_id=data['veterinaryID'],
            lameness_right_front=data.get('lamenessRightFront'),
            lameness_left_front=data.get('lamenessLeftFront'),
            lameness_right_hind=data.get('lamenessRighHind'),
            lameness_left_hind=data.get('lamenessLeftHind')
        )
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            "idAppointment": appointment.id,
            "horseId": appointment.horse_id,
            "veterinaryID": appointment.veterinary_id,
            "lamenessRightFront": appointment.lameness_right_front,
            "lamenessLeftFront": appointment.lameness_left_front,
            "lamenessRighHind": appointment.lameness_right_hind,
            "lamenessLeftHind": appointment.lameness_left_hind
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@appointments_bp.route('/appointments', methods=['GET'])
def get_appointments():
    try:
        appointments = Appointment.query.all()
        appointments_list = [{
            "idAppointment": appt.id,
            "horseId": appt.horse_id,
            "veterinaryID": appt.veterinary_id,
            "lamenessRightFront": appt.lameness_right_front,
            "lamenessLeftFront": appt.lameness_left_front,
            "lamenessRighHind": appt.lameness_right_hind,
            "lamenessLeftHind": appt.lameness_left_hind
        } for appt in appointments]
        
        return jsonify(appointments_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500