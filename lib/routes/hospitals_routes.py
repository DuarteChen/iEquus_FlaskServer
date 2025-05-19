import os
import logging # Changed from 'from venv import logger'
from flask import Blueprint, jsonify, url_for, request
from lib.models import Hospital

hospitals_bp = Blueprint('hospitals_bp', __name__)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOSPITAL_LOGOS_FOLDER = os.path.join('hospitals', 'hospitals_logos')

# It's good practice to get a logger specific to this module
logger = logging.getLogger(__name__)

def hospitalToJson(hospital):
    admin_info = None
    if hospital.admin_veterinarian: # Access the relationship
        admin_info = {
            "idVeterinarian": hospital.admin_veterinarian.id,
            "name": hospital.admin_veterinarian.name
        }

    return {
        "id": hospital.id,
        "name": hospital.name,
        "logoPath": _get_image_url_hospital(hospital.logoPath),
        "admin": admin_info # Includes admin vet's ID and name
    }


def _get_image_url_hospital(filename):
    if not filename:
        return None
    try:
        # Use HOSPITAL_LOGOS_FOLDER to construct the path
        relative_path = os.path.join(HOSPITAL_LOGOS_FOLDER, filename).replace('\\', '/')
        return url_for('static', filename=relative_path, _external=True)
    
    except RuntimeError as e:
        logger.error(f"Error generating URL for {filename}: {e}")
        return None

@hospitals_bp.route('/hospitals', methods=['GET'])
def get_all_hospitals():
    """
    Retrieves all hospitals.
    """
    hospitals = Hospital.query.all()
    hospitals_list = [hospitalToJson(hospital) for hospital in hospitals]
    return jsonify(hospitals_list), 200

@hospitals_bp.route('/hospital/<int:hospital_id>', methods=['GET'])
def get_hospital_by_id(hospital_id):
    """
    Retrieves a specific hospital by its ID.
    """
    hospital = Hospital.query.filter_by(id=hospital_id).first()
    if hospital:
        return jsonify(hospitalToJson(hospital)), 200
    else:
        return jsonify({"error": "Hospital not found"}), 404