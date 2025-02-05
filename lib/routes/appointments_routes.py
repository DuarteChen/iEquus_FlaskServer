from flask import Blueprint, request, jsonify
from lib.models import Appointment, db

appointments_bp = Blueprint('appointments', __name__)

# Add an appointment
@appointments_bp.route('/appointments', methods=['POST'])
def add_appointment():
    try:
        data = request.get_json()
        if 'horseId' not in data or 'veterinarianId' not in data:
            return jsonify({"error": "horseId and veterinarianId are required"}), 400
        
        appointment = Appointment(
            horseId=data['horseId'],
            veterinarianId=data['veterinarianId'],
            lamenessRightFront=data.get('lamenessRightFront'),
            lamenessLeftFront=data.get('lamenessLeftFront'),
            lamenessRighHind=data.get('lamenessRightHind'),
            lameness_left_hind=data.get('lamenessLeftHind'),
            BPM=data.get('BPM'),
            muscleTensionFrequency=data.get('muscleTensionFrequency'),
            muscleTensionStifness=data.get('muscleTensionStiffness'),
            muscleTensionR=data.get('muscleTensionR'),
            CBCpath=data.get('CBCpath'),
            comment=data.get('comment')
        )
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({"message": "Appointment added successfully", "id": appointment.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get all appointments
@appointments_bp.route('/appointments', methods=['GET'])
def get_appointments():
    try:
        appointments = Appointment.query.all()
        appointments_list = [{
            "id": appt.id,
            "horseId": appt.horseId,
            "veterinarianId": appt.veterinarianId,
            "lamenessRightFront": appt.lamenessRightFront,
            "lamenessLeftFront": appt.lamenessLeftFront,
            "lamenessRightHind": appt.lamenessRighHind,
            "lamenessLeftHind": appt.lameness_left_hind,
            "BPM": appt.BPM,
            "muscleTensionFrequency": appt.muscleTensionFrequency,
            "muscleTensionStiffness": appt.muscleTensionStifness,
            "muscleTensionR": appt.muscleTensionR,
            "CBCpath": appt.CBCpath,
            "comment": appt.comment
        } for appt in appointments]
        
        return jsonify(appointments_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get appointments by horse ID
@appointments_bp.route('/appointments/horse/<int:horseId>', methods=['GET'])
def get_appointments_by_horse(horseId):
    try:
        appointments = Appointment.query.filter_by(horseId=horseId).all()
        if not appointments:
            return jsonify({"message": "No appointments found for this horse"}), 404
        
        appointments_list = [{
            "id": appt.id,
            "horseId": appt.horseId,
            "veterinarianId": appt.veterinarianId,
            "lamenessRightFront": appt.lamenessRightFront,
            "lamenessLeftFront": appt.lamenessLeftFront,
            "lamenessRightHind": appt.lamenessRighHind,
            "lamenessLeftHind": appt.lameness_left_hind,
            "BPM": appt.BPM,
            "muscleTensionFrequency": appt.muscleTensionFrequency,
            "muscleTensionStiffness": appt.muscleTensionStifness,
            "muscleTensionR": appt.muscleTensionR,
            "CBCpath": appt.CBCpath,
            "comment": appt.comment
        } for appt in appointments]
        
        return jsonify(appointments_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Update an appointment
@appointments_bp.route('/appointments/<int:appointmentId>', methods=['PUT'])
def update_appointment(appointmentId):
    try:
        data = request.get_json()
        appointment = Appointment.query.get(appointmentId)
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404
        
        for key, value in data.items():
            if hasattr(appointment, key):
                setattr(appointment, key, value)
        
        db.session.commit()
        return jsonify({"message": "Appointment updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete an appointment
@appointments_bp.route('/appointments/<int:appointmentId>', methods=['DELETE'])
def delete_appointment(appointmentId):
    try:
        appointment = Appointment.query.get(appointmentId)
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404
        
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({"message": "Appointment deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500