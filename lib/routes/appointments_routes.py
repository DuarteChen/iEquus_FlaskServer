from tkinter import Image
from flask import Blueprint, request, jsonify
from lib.models import Appointment, db
import os
from werkzeug.utils import secure_filename
import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import subprocess

appointments_bp = Blueprint('appointments', __name__)
project_dir = os.getcwd()  # This will give you the current working directory
cbcFolder = os.path.join(project_dir, 'lib','static', 'appointments', 'cbc')


def convert_to_pdf(input_path, output_path):
    try:
        file_ext = os.path.splitext(input_path)[1].lower()

        # If the file is already a PDF, simply rename/move it
        if file_ext == '.pdf':
            os.rename(input_path, output_path)
            return

        # For Image Files (JPG, PNG, BMP, etc.)
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            image = Image.open(input_path)
            rgb_image = image.convert('RGB')  # Ensure it's in RGB mode
            rgb_image.save(output_path, "PDF")
            return

        # For Text Files (TXT)
        if file_ext == '.txt':
            with open(input_path, 'r') as file:
                text = file.read()
            
            c = canvas.Canvas(output_path, pagesize=letter)
            c.drawString(100, 750, text[:1000])  # Draw first 1000 chars (adjust as needed)
            c.save()
            return

        # For Office Files (DOCX, XLSX, PPTX) using LibreOffice
        if file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', os.path.dirname(output_path), input_path], check=True)
            converted_pdf = os.path.join(os.path.dirname(input_path), os.path.splitext(os.path.basename(input_path))[0] + '.pdf')
            os.rename(converted_pdf, output_path)
            return

        # Fallback for unsupported formats
        raise Exception(f"Unsupported file format: {file_ext}")

    except Exception as e:
        raise Exception(f"Error converting file to PDF: {str(e)}")

@appointments_bp.route('/appointments', methods=['POST'])
def add_appointment():
    try:
        # Get form data instead of JSON
        horse_id = request.form.get('horseId')
        veterinarian_id = request.form.get('veterinarianId')

        if not horse_id or not veterinarian_id:
            return jsonify({"error": "horseId and veterinarianId are required"}), 400

        # Handle CBC file upload if present
        cbc_file = request.files.get('CBCfile')  # File key: CBCfile
        cbc_path = None
        if cbc_file:
            filename = secure_filename(cbc_file.filename)
            temp_path = os.path.join(cbcFolder, f"temp_{filename}")
            cbc_file.save(temp_path)  # Temporarily save

            cbc_path = temp_path
            
            # Optionally convert the file to PDF if needed
            convert_to_pdf(cbc_path, cbc_path)

        # Create the appointment
        appointment = Appointment(
            horseId=horse_id,
            veterinarianId=veterinarian_id,
            lamenessRightFront=request.form.get('lamenessRightFront'),
            lamenessLeftFront=request.form.get('lamenessLeftFront'),
            lamenessRighHind=request.form.get('lamenessRightHind'),
            lamenessLeftHind=request.form.get('lamenessLeftHind'),
            BPM=request.form.get('BPM'),
            muscleTensionFrequency=request.form.get('muscleTensionFrequency'),
            muscleTensionStifness=request.form.get('muscleTensionStiffness'),
            muscleTensionR=request.form.get('muscleTensionR'),
            comment=request.form.get('comment'),
            CBCpath=cbc_path  # Temporarily assigned path
        )

        # Save to the database
        db.session.add(appointment)
        db.session.commit()

        # Rename CBC file to final name using appointment ID
        if cbc_path:
            new_cbc_path = os.path.join(cbcFolder, f"horse{appointment.horseId}_appointment{appointment.id}.pdf")
            os.rename(cbc_path, new_cbc_path)

            # Update appointment with the correct CBC path
            appointment.CBCpath = new_cbc_path
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
            "lamenessLeftHind": appt.lamenessLeftHind,
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
            "lamenessLeftHind": appt.lamenessLeftHind,
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

@appointments_bp.route('/appointments/<int:appointmentId>', methods=['PUT'])
def update_appointment(appointmentId):
    try:
        # Retrieve the appointment
        appointment = Appointment.query.get(appointmentId)
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404

        # Update regular appointment fields from form data
        updatable_fields = [
            'veterinarianId', 'lamenessRightFront', 'lamenessLeftFront',
            'lamenessRightHind', 'lamenessLeftHind', 'BPM', 
            'muscleTensionFrequency', 'muscleTensionStiffness', 
            'muscleTensionR', 'comment'
        ]

        for field in updatable_fields:
            if field in request.form:
                setattr(appointment, field, request.form.get(field))

        # Handle CBC file upload if provided
        cbc_file = request.files.get('CBCfile')  # Expecting the file with key 'CBCfile'
        if cbc_file:
            # Delete the old CBC file if it exists
            if appointment.CBCpath and os.path.exists(appointment.CBCpath):
                os.remove(appointment.CBCpath)

            # Save new CBC file
            filename = secure_filename(cbc_file.filename)
            temp_path = os.path.join(cbcFolder, f"temp_{filename}")
            cbc_file.save(temp_path)

            # Convert to PDF if necessary
            final_cbc_path = os.path.join(cbcFolder, f"horse{appointment.horseId}_appointment{appointment.id}.pdf")
            convert_to_pdf(temp_path, final_cbc_path)
            os.remove(temp_path)  # Remove the temporary file

            # Update the appointment's CBC path
            appointment.CBCpath = final_cbc_path

        # Commit all changes to the database
        db.session.commit()

        return jsonify({"message": "Appointment updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete an appointment
@appointments_bp.route('/appointments/<int:appointmentId>', methods=['DELETE'])
def delete_appointment(appointmentId):
    try:
        # Retrieve the appointment
        appointment = Appointment.query.get(appointmentId)
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404

        # Delete the associated CBC file if it exists
        if appointment.CBCpath and os.path.exists(appointment.CBCpath):
            os.remove(appointment.CBCpath)

        # Delete the appointment from the database
        db.session.delete(appointment)
        db.session.commit()

        return jsonify({"message": "Appointment and associated CBC file deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500