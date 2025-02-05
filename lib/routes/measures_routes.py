from flask import Blueprint, request, jsonify
from lib.models import Measure, db

measures_bp = Blueprint('measures', __name__)

# Add a measure
@measures_bp.route('/measures', methods=['POST'])
def add_measure():
    data = request.get_json()
    new_measure = Measure(
        userBW=data.get('userBW'),
        algorithmBW=data.get('algorithmBW'),
        userBCS=data.get('userBCS'),
        algorithmBCS=data.get('algorithmBCS'),
        date=data['date'],
        coordinates=data.get('coordinates'),
        picturePath=data['picturePath'],
        favorite=data.get('favorite'),
        horseId=data['horseId'],
        veterinarianId=data.get('veterinarianId'),
        appointmentId=data.get('appointmentId')
    )
    db.session.add(new_measure)
    db.session.commit()
    return jsonify({'message': 'Measure added successfully'}), 201

# Get all measures
@measures_bp.route('/measures', methods=['GET'])
def get_measures():
    measures = Measure.query.all()
    return jsonify([measure.to_dict() for measure in measures]), 200

# Get measures by horse ID
@measures_bp.route('/measures/horse/<int:horseId>', methods=['GET'])
def get_measures_by_horse(horseId):
    measures = Measure.query.filter_by(horseId=horseId).all()
    return jsonify([measure.to_dict() for measure in measures]), 200

# Get measures by appointment ID
@measures_bp.route('/measures/appointment/<int:appointment_id>', methods=['GET'])
def get_measures_by_appointment(appointment_id):
    measures = Measure.query.filter_by(appointmentId=appointment_id).all()
    return jsonify([measure.to_dict() for measure in measures]), 200

# Update a measure
@measures_bp.route('/measures/<int:measure_id>', methods=['PUT'])
def update_measure(measure_id):
    measure = Measure.query.get_or_404(measure_id)
    data = request.get_json()
    for key, value in data.items():
        if hasattr(measure, key):
            setattr(measure, key, value)
    db.session.commit()
    return jsonify({'message': 'Measure updated successfully'}), 200

# Delete a measure
@measures_bp.route('/measures/<int:measure_id>', methods=['DELETE'])
def delete_measure(measure_id):
    measure = Measure.query.get_or_404(measure_id)
    db.session.delete(measure)
    db.session.commit()
    return jsonify({'message': 'Measure deleted successfully'}), 200
