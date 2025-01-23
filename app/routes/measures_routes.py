from flask import Blueprint, request, jsonify
from app.models import Measure, db

measures_bp = Blueprint('measures', __name__)

@measures_bp.route('/measures', methods=['POST'])
def add_measure():
    try:
        data = request.get_json()
        if 'vetAppointment' not in data:
            return jsonify({"error": "vetAppointment is required"}), 400
        
        measure = Measure(
            vet_appointment=data['vetAppointment'],
            user_bw=data.get('userBW'),
            algorithm_bw=data.get('algorithmBW'),
            user_bcs=data.get('userBCS'),
            algorithm_bcs=data.get('algorithmBCS'),
            bpm=data.get('BPM'),
            ecg_time=data.get('ECGtime'),
            muscle_tension_frequency=data.get('muscleTensionFrequency'),
            muscle_tension_stifness=data.get('muscleTensionStifness'),
            muscle_tension_r=data.get('muscleTensionR')
        )
        db.session.add(measure)
        db.session.commit()
        
        return jsonify({
            "idMeasure": measure.id,
            "vetAppointment": measure.vet_appointment,
            "userBW": measure.user_bw,
            "algorithmBW": measure.algorithm_bw,
            "userBCS": measure.user_bcs,
            "algorithmBCS": measure.algorithm_bcs,
            "BPM": measure.bpm,
            "ECGtime": measure.ecg_time,
            "muscleTensionFrequency": measure.muscle_tension_frequency,
            "muscleTensionStifness": measure.muscle_tension_stifness,
            "muscleTensionR": measure.muscle_tension_r
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@measures_bp.route('/measures', methods=['GET'])
def get_measures():
    try:
        measures = Measure.query.all()
        measures_list = [{
            "idMeasure": m.id,
            "vetAppointment": m.vet_appointment,
            "userBW": m.user_bw,
            "algorithmBW": m.algorithm_bw,
            "userBCS": m.user_bcs,
            "algorithmBCS": m.algorithm_bcs,
            "BPM": m.bpm,
            "ECGtime": m.ecg_time,
            "muscleTensionFrequency": m.muscle_tension_frequency,
            "muscleTensionStifness": m.muscle_tension_stifness,
            "muscleTensionR": m.muscle_tension_r
        } for m in measures]
        
        return jsonify(measures_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500