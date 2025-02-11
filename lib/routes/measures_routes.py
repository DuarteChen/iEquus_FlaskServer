from flask import Blueprint, json, request, jsonify
import requests
from lib.models import Measure, db
from PIL import Image
import os

measures_bp = Blueprint('measures', __name__)

project_dir = os.getcwd()
algorithm_PicturesFolder = os.path.join(project_dir, 'lib','static', 'measures')

# Add a measure
@measures_bp.route('/measures', methods=['POST'])
def add_measure():
    try:
        # Get form data
        veterinarianId = request.form.get('veterinarianId')
        horseId = request.form.get('horseId')
        date = request.form.get('date')
        appointmentId = request.form.get('appointmentId')
        userBW = request.form.get('userBW')
        userBCS = request.form.get('userBCS')

        # Coordinates are expected as JSON string in form data
        coordinates = request.form.get('coordinates')
        if coordinates:
            coordinates = json.loads(coordinates)

        measure = Measure(
            veterinarianId=veterinarianId,
            horseId=horseId,
            date=date,
            appointmentId=appointmentId,
            coordinates=coordinates,
            userBW=userBW,
            userBCS=userBCS,
        )

        db.session.add(measure)
        db.session.flush() 

        # Handle coordinates and picture if both are provided
        if coordinates and 'picturePath' in request.files:
            results = forward_coordinates(coordinates)
            measure.algorithmBW = results.get('algorithmBW_result', 0)
            measure.algorithmBCS = results.get('algorithmBCS_result', 0)

            # Handle picture upload
            file = request.files['picturePath']
            image = Image.open(file)


            algorithm_Picture_FileName = f"{measure.id}_algorithmPicture_{measure.horseId}_horseId.png"
            algorithm_PicturesPath = os.path.join(algorithm_PicturesFolder, algorithm_Picture_FileName)

            image.save(algorithm_PicturesPath, "PNG", quality=100)
            measure.picturePath = algorithm_PicturesPath

        db.session.commit()
        return jsonify({'message': f"Measure added successfully with Measure ID: {measure.id}"}), 201

    except Exception as e:
        db.session.rollback()  # Rollback on error
        return jsonify({'message': str(e)}), 500


# Get all measures
@measures_bp.route('/measures', methods=['GET'])
def get_measures():
    try:
        measures = Measure.query.all()  # Fetch all records from the Measure table
        measures_list = []

        # Convert each measure object to a dictionary and append to the list
        for measure in measures:
            measures_list.append({
                'id': measure.id,
                'veterinarianId': measure.veterinarianId,
                'horseId': measure.horseId,
                'date': measure.date,
                'appointmentId': measure.appointmentId,
                'coordinates': measure.coordinates,
                'userBW': measure.userBW,
                'userBCS': measure.userBCS,
                'algorithmBW': measure.algorithmBW,
                'algorithmBCS': measure.algorithmBCS,
                'picturePath': measure.picturePath
            })

        return jsonify({'measures': measures_list}), 200

    except Exception as e:
        return jsonify({'message': f"Error fetching measures: {str(e)}"}), 500

# Get measures by horse ID
@measures_bp.route('/measures/horse/<int:horseId>', methods=['GET'])
def get_measures_by_horse(horseId):
    try:
        # Query measures where horseId matches the given parameter
        measures = Measure.query.filter_by(horseId=horseId).all()

        if not measures:
            return jsonify({'message': f'No measures found for horse ID {horseId}'}), 404
        
        measures_list = []
        for measure in measures:
            measures_list.append({
                'id': measure.id,
                'veterinarianId': measure.veterinarianId,
                'horseId': measure.horseId,
                'date': measure.date,
                'appointmentId': measure.appointmentId,
                'coordinates': measure.coordinates,
                'userBW': measure.userBW,
                'userBCS': measure.userBCS,
                'algorithmBW': measure.algorithmBW,
                'algorithmBCS': measure.algorithmBCS,
                'picturePath': measure.picturePath
            })
        
        return jsonify({'measures': measures_list}), 200

    except Exception as e:
        return jsonify({'message': f"Error fetching measures for horse ID {horseId}: {str(e)}"}), 500

# Get measures by appointment ID
@measures_bp.route('/measures/appointment/<int:appointment_id>', methods=['GET'])
def get_measures_by_appointment(appointment_id):
    try:
        # Query measures where appointmentId matches the given parameter
        measures = Measure.query.filter_by(appointmentId=appointment_id).all()

        if not measures:
            return jsonify({'message': f'No measures found for appointment ID {appointment_id}'}), 404
        
        measures_list = []
        for measure in measures:
            measures_list.append({
                'id': measure.id,
                'veterinarianId': measure.veterinarianId,
                'horseId': measure.horseId,
                'date': measure.date,
                'appointmentId': measure.appointmentId,
                'coordinates': measure.coordinates,
                'userBW': measure.userBW,
                'userBCS': measure.userBCS,
                'algorithmBW': measure.algorithmBW,
                'algorithmBCS': measure.algorithmBCS,
                'picturePath': measure.picturePath
            })
        
        return jsonify({'measures': measures_list}), 200

    except Exception as e:
        return jsonify({'message': f"Error fetching measures for appointment ID {appointment_id}: {str(e)}"}), 500

@measures_bp.route('/measures/<int:measure_id>', methods=['PUT'])
def update_measure(measure_id):
    try:
        # Retrieve the measure by its ID
        measure = Measure.query.get(measure_id)

        if not measure:
            return jsonify({'message': f'Measure with ID {measure_id} not found'}), 404

        data = request.form

        # Update the fields of the measure
        if 'veterinarianId' in data:
            measure.veterinarianId = data['veterinarianId']
        if 'horseId' in data:
            measure.horseId = data['horseId']
        if 'date' in data:
            measure.date = data['date']
        if 'appointmentId' in data:
            measure.appointmentId = data['appointmentId']
        if 'coordinates' in data:
            try:
                coordinates = json.loads(data['coordinates'])
                measure.coordinates = coordinates
            except json.JSONDecodeError:
                return jsonify({'message': 'Invalid JSON format for coordinates'}), 400
        if 'userBW' in data:
            measure.userBW = data['userBW']
        if 'userBCS' in data:
            measure.userBCS = data['userBCS']

        # If coordinates and picturePath are present in the request
        if 'coordinates' in data:
            if 'picturePath' in request.files:

                results = forward_coordinates(coordinates)
                algorithmBW_result = results.get('algorithmBW_result', 0)
                algorithmBCS_result = results.get('algorithmBCS_result', 0)

                measure.algorithmBW = algorithmBW_result if algorithmBW_result else None
                measure.algorithmBCS = algorithmBCS_result if algorithmBCS_result else None

                # Handle picture update
                # Check if there is an old picture to delete
                if measure.picturePath and os.path.exists(measure.picturePath):
                    os.remove(measure.picturePath)  # Delete the old picture

                # Upload new picture
                file = request.files['picturePath']
                image = Image.open(file)

                algorithm_Picture_FileName = f"{measure.id}_algorithmPicture_{measure.horseId}_horseId.png"
                algorithm_PicturesPath = os.path.join(algorithm_PicturesFolder, algorithm_Picture_FileName)

                image.save(algorithm_PicturesPath, "PNG", quality=100)
                measure.picturePath = algorithm_PicturesPath

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': f'Measure with ID {measure.id} updated successfully'}), 200

    except Exception as e:
        db.session.rollback()  # Rollback on error
        return jsonify({'message': f'Error updating measure: {str(e)}'}), 500


# Delete a measure
@measures_bp.route('/measures/<int:measure_id>', methods=['DELETE'])
def delete_measure(measure_id):
    measure = Measure.query.get_or_404(measure_id)
    db.session.delete(measure)
    db.session.commit()
    return jsonify({'message': 'Measure deleted successfully'}), 200



#--------------------------------------------------------------------------------
SUM_SERVER_URL = 'http://localhost:9097/sum_coordinates'

def forward_coordinates(coordinates):
    # Validate the input format
    if not isinstance(coordinates, dict):
        return {'error': 'Coordinates must be a dictionary with coordinate IDs as keys'}, 400
    
    try:
        response = requests.post(SUM_SERVER_URL, json={'coordinates': coordinates})
        if response.status_code != 200:
            return {'error': 'Failed to get sum from sum_coordinates server'}, 500
        response_data = response.json()
        return {
            'algorithmBW_result': response_data.get('sum', 0),  # Total sum of x and y
            'algorithmBCS_result': response_data.get('multiplication_sum', 0)  # Sum of x * y
        }
    except requests.RequestException as e:
        return {'error': f'Error connecting to sum_coordinates server: {e}'}, 500