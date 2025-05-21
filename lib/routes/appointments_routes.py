import logging
import os
from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from lib.models import Appointment, db, Veterinarian, Horse
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType
from werkzeug.datastructures import FileStorage
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
import subprocess

appointments_bp = Blueprint('appointments', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATIC_FOLDER_REL = os.path.join('lib', 'static')
APPOINTMENTS_FOLDER_REL = os.path.join(STATIC_FOLDER_REL, 'appointments')
CBC_FOLDER_REL = os.path.join(APPOINTMENTS_FOLDER_REL, 'cbc')


CBC_FOLDER = os.path.join(project_dir, CBC_FOLDER_REL)

os.makedirs(CBC_FOLDER, exist_ok=True)
logger.info(f"CBC Upload folder set to: {CBC_FOLDER}")



def convert_to_pdf(input_path, output_path):
    """
    Converts various file types (images, text, office docs) to PDF.
    Handles existing PDFs by renaming.
    Raises:
        Exception: If conversion fails or format is unsupported.
    """
    try:
        file_ext = os.path.splitext(input_path)[1].lower()
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Attempting to convert '{input_path}' (ext: {file_ext}) to PDF '{output_path}'")


        if file_ext == '.pdf':
            logger.info("Input is already PDF. Renaming/Moving.")

            if os.path.exists(output_path):
                 os.remove(output_path)
            os.rename(input_path, output_path)
            return


        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']:
            logger.info("Converting image file using Pillow.")
            with PILImage.open(input_path) as image:

                if image.mode == 'RGBA' or image.mode == 'P':
                    image = image.convert('RGB')
                image.save(output_path, "PDF", resolution=100.0, save_all=True)
            logger.info("Image conversion successful.")
            return


        if file_ext == '.txt':
            logger.info("Converting text file using reportlab.")

            c = canvas.Canvas(output_path, pagesize=letter)
            text_object = c.beginText(40, 750)
            text_object.setFont("Times-Roman", 10)
            line_height = 12

            with open(input_path, 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:

                    current_line = ""
                    for word in line.split():
                        test_line = f"{current_line} {word}".strip()

                        if c.stringWidth(test_line, "Times-Roman", 10) < (letter[0] - 80):
                            current_line = test_line
                        else:
                            text_object.textLine(current_line)
                            current_line = word
                            if text_object.getY() < 50:
                                c.drawText(text_object)
                                c.showPage()
                                text_object = c.beginText(40, 750)
                                text_object.setFont("Times-Roman", 10)
                    text_object.textLine(current_line)
                    if text_object.getY() < 50:
                        c.drawText(text_object)
                        c.showPage()
                        text_object = c.beginText(40, 750)
                        text_object.setFont("Times-Roman", 10)

            c.drawText(text_object)
            c.save()
            logger.info("Text conversion successful.")
            return


        if file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']:
            logger.info("Converting office document using LibreOffice.")

            base_name = os.path.splitext(os.path.basename(input_path))[0]

            libreoffice_output_pdf = os.path.join(output_dir, f"{base_name}.pdf")


            if os.path.exists(libreoffice_output_pdf):
                 logger.warning(f"Removing existing potential LibreOffice output: {libreoffice_output_pdf}")
                 os.remove(libreoffice_output_pdf)

            if os.path.exists(output_path):
                 logger.warning(f"Removing existing final target file before conversion: {output_path}")
                 os.remove(output_path)

            try:

                cmd = ['libreoffice', '--headless', '--invisible', '--convert-to', 'pdf', '--outdir', output_dir, input_path]
                logger.info(f"Running LibreOffice command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                logger.info(f"LibreOffice stdout: {result.stdout}")

                if result.stderr:
                    logger.warning(f"LibreOffice stderr: {result.stderr}")


                if not os.path.exists(libreoffice_output_pdf):
                    raise FileNotFoundError(f"LibreOffice did not create the expected PDF file: {libreoffice_output_pdf}")


                os.rename(libreoffice_output_pdf, output_path)
                logger.info(f"Office document conversion successful. Output at: {output_path}")
                return

            except FileNotFoundError:
                 logger.error("LibreOffice command not found. Is LibreOffice installed and in the system PATH?")
                 raise Exception("Conversion tool (LibreOffice) not found.")
            except subprocess.TimeoutExpired:
                 logger.error(f"LibreOffice conversion timed out for file: {input_path}")
                 raise Exception("LibreOffice conversion timed out.")
            except subprocess.CalledProcessError as cpe:
                 logger.error(f"LibreOffice conversion failed with exit code {cpe.returncode} for file '{input_path}'")
                 logger.error(f"LibreOffice stderr: {cpe.stderr}")
                 logger.error(f"LibreOffice stdout: {cpe.stdout}")

                 if os.path.exists(libreoffice_output_pdf):
                     try:
                         os.remove(libreoffice_output_pdf)
                     except OSError as ose:
                         logger.warning(f"Could not remove intermediate LibreOffice file '{libreoffice_output_pdf}': {ose}")
                 raise Exception(f"LibreOffice conversion failed.")


        logger.warning(f"Unsupported file format encountered for PDF conversion: {file_ext}")
        raise ValueError(f"Unsupported file format for PDF conversion: {file_ext}")

    except Exception as e:
        logger.exception(f"Error during PDF conversion process for '{input_path}': {str(e)}")

        # Attempt to clean up any intermediate file LibreOffice might have created
        # This is the file LibreOffice would create in output_dir before a potential rename
        # It's important to clean this up if the process failed after its creation but before successful rename/cleanup.
        # This path is constructed based on how LibreOffice names its output with --outdir
        libreoffice_output_pdf_check = os.path.join(os.path.dirname(output_path), f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf")
        if os.path.exists(libreoffice_output_pdf_check) and libreoffice_output_pdf_check != output_path:
             try:
                 os.remove(libreoffice_output_pdf_check)
                 logger.info(f"Cleaned up intermediate libreoffice output: {libreoffice_output_pdf_check}")
             except OSError as ose:
                 logger.warning(f"Could not remove intermediate LibreOffice file during error cleanup '{libreoffice_output_pdf_check}': {ose}")

        raise Exception(f"Error converting file to PDF: {str(e)}")


def _save_and_convert_cbc(cbc_file: FileStorage, horse_id, appointment_id):
    """
    Saves temporary file from FileStorage, converts to PDF,
    renames to final path, and cleans up temp file.
    Returns the final relative PDF filename or None.
    Raises:
        ValueError: If filename is invalid or saving/conversion fails.
    """
    if not cbc_file or not cbc_file.filename:
        return None

    temp_path = None
    try:

        original_filename = cbc_file.filename
        safe_filename = secure_filename(original_filename)
        if not safe_filename:
            raise ValueError("Invalid CBC file name provided (secure_filename check failed).")


        _, file_ext = os.path.splitext(safe_filename)
        if not file_ext:
             _, file_ext = os.path.splitext(original_filename)
             if not file_ext:
                 raise ValueError("Could not determine file extension for CBC file.")


        temp_filename = f"temp_{appointment_id}{file_ext}"
        temp_path = os.path.join(CBC_FOLDER, temp_filename)
        final_filename = f"cbc_horse{horse_id}_appointment{appointment_id}.pdf"
        final_pdf_path = os.path.join(CBC_FOLDER, final_filename)


        logger.info(f"Saving uploaded CBC file temporarily to: {temp_path}")
        cbc_file.save(temp_path)


        logger.info(f"Converting temporary file '{temp_path}' to final PDF '{final_pdf_path}'")
        convert_to_pdf(temp_path, final_pdf_path)

        logger.info(f"Successfully converted and saved CBC PDF to: {final_pdf_path}")

        return final_filename

    except (ValueError, Exception) as e:
        logger.exception(f"Failed to process CBC file for appointment {appointment_id}, filename '{original_filename}': {e}")
        raise ValueError(f"Failed to process CBC file: {str(e)}")
    finally:

        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Removed temporary file: {temp_path}")
            except OSError as e:
                logger.warning(f"Could not remove temporary file '{temp_path}': {e}")

def _get_cbc_url(filename):
    """Generates the absolute URL for a CBC PDF file."""
    if not filename:
        return None
    try:

        relative_path = os.path.join('appointments', 'cbc', filename).replace('\\', '/')
        return url_for('static', filename=relative_path, _external=True)
    except RuntimeError as e:
        logger.error(f"Error generating URL for CBC file {filename}: {e}")
        return None

def _delete_cbc_pdf(filename):
    """Deletes a CBC PDF file if it exists."""
    if not filename:
        return False
    try:
        path = os.path.join(CBC_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted CBC PDF file: {path}")
            return True
        else:
            logger.warning(f"Attempted to delete non-existent CBC PDF file: {path}")
            return False
    except OSError as e:
        logger.error(f"Error deleting CBC PDF file {path}: {e}")
        return False



@appointments_bp.route('/appointment', methods=['POST'])
@jwt_required()
def add_appointment():
    """
    Adds a new appointment. Expects multipart/form-data.
    Required form fields: 'horseId', 'veterinarianId'.
    Optional form fields: 'lamenessRightFront', 'lamenessLeftFront', 'lamenessRightHind',
                          'lamenessLeftHind', 'BPM', 'ECGtime', 'muscleTensionFrequency', # noqa: E501
                          'muscleTensionStiffness', 'muscleTensionR', 'comment'.
    Optional file upload: 'cbcFile'.
    """
    requesting_vet_id_str = None # For logging
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for add_appointment: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_veterinarian = Veterinarian.query.get(requesting_vet_id)
        if not requesting_veterinarian:
            logger.warning(f"Veterinarian with ID {requesting_vet_id} from token not found (in add_appointment).")
            return jsonify({"error": "Authenticated veterinarian not found"}), 404

        horse_id_str = request.form.get('horseId')
        try:
            if horse_id_str is None: raise ValueError("horseId form field is required.")
            horse_id = int(horse_id_str)
        except (ValueError, TypeError) as ve:
             raise BadRequest(f"Invalid horseId in form data: {ve}")

        horse = Horse.query.get(horse_id)
        if not horse:
            raise NotFound(f"Horse with id {horse_id} not found.")

        # Authorization: Check if the requesting vet can create appointments for this horse
        can_access_horse = False
        if horse.veterinarianId == requesting_vet_id:
            can_access_horse = True
        elif requesting_veterinarian.hospitalId is not None and \
             horse.veterinarian and \
             horse.veterinarian.hospitalId == requesting_veterinarian.hospitalId:
            can_access_horse = True

        if not can_access_horse:
            logger.warning(f"Veterinarian {requesting_vet_id} attempt to create appointment for horse {horse_id} without permission.")
            return jsonify({"error": "Forbidden. You do not have permission to create appointments for this horse."}), 403

        lameness_rf = request.form.get('lamenessRightFront', type=int, default=None)
        lameness_lf = request.form.get('lamenessLeftFront', type=int, default=None)
        lameness_rh = request.form.get('lamenessRightHind', type=int, default=None)
        lameness_lh = request.form.get('lamenessLeftHind', type=int, default=None)
        bpm = request.form.get('BPM', type=int, default=None)
        ecg_time = request.form.get('ECGtime', type=int, default=None)
        muscle_freq = request.form.get('muscleTensionFrequency')
        muscle_stiff = request.form.get('muscleTensionStiffness')
        muscle_r = request.form.get('muscleTensionR')
        comment = request.form.get('comment')


        appointment = Appointment(
            horseId=horse_id,
            veterinarianId=requesting_vet_id, # Assign to the logged-in veterinarian
            lamenessRightFront=lameness_rf,
            lamenessLeftFront=lameness_lf,
            lamenessRightHind=lameness_rh,
            lamenessLeftHind=lameness_lh,
            BPM=bpm,
            muscleTensionFrequency=muscle_freq,
            muscleTensionStiffness=muscle_stiff,
            muscleTensionR=muscle_r,
            comment=comment,
            ECGtime=ecg_time,
            CBCpath=None
        )
        db.session.add(appointment)
        db.session.flush()
        logger.info(f"Appointment object created with temporary ID {appointment.id}")


        cbc_file = request.files.get('cbcFile')
        final_cbc_filename = None

        if cbc_file:
            logger.info(f"Processing uploaded CBC file: {cbc_file.filename} for new appointment {appointment.id}")
            try:
                final_cbc_filename = _save_and_convert_cbc(
                    cbc_file, horse_id, appointment.id
                )
                appointment.CBCpath = final_cbc_filename
                logger.info(f"CBC path (filename) set to: {final_cbc_filename}")
            except ValueError as e:
                 db.session.rollback()
                 logger.error(f"Error processing CBC file during add: {e}")
                 raise BadRequest(f"Error processing CBC file: {e}")
            except Exception as e:
                 db.session.rollback()
                 logger.exception("Unexpected error during CBC file processing for add.")
                 raise Exception("An unexpected error occurred while processing the CBC file.")


        db.session.commit()
        logger.info(f"Appointment {appointment.id} committed successfully.")


        return jsonify({
            "message": "Appointment added successfully",
            "appointment": {
                "id": appointment.id,
                "horseId": appointment.horseId,
                "veterinarianId": appointment.veterinarianId,
                "date": appointment.date.isoformat() if appointment.date else None,
                "lamenessRightFront": appointment.lamenessRightFront,
                "lamenessLeftFront": appointment.lamenessLeftFront,
                "lamenessRightHind": appointment.lamenessRightHind,
                "lamenessLeftHind": appointment.lamenessLeftHind,
                "BPM": appointment.BPM,
                "ECGtime": appointment.ECGtime,
                "muscleTensionFrequency": appointment.muscleTensionFrequency,
                "muscleTensionStiffness": appointment.muscleTensionStiffness,
                "muscleTensionR": appointment.muscleTensionR,
                "CBCpath": _get_cbc_url(appointment.CBCpath),
                "comment": appointment.comment,
            }
        }), 201

    except (BadRequest, NotFound, UnsupportedMediaType) as e:
        logger.warning(f"Client error adding appointment: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        # db.session.rollback() might have already been called if an error occurred during db.flush() or db.commit()
        db.session.rollback()
        logger.exception("Server error adding appointment.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@appointments_bp.route('/appointments', methods=['GET'])
@jwt_required()
def get_appointments():
    """
    Gets a list of appointments associated with the veterinarian identified by the JWT token.
    """
    requesting_vet_id_str = None # For logging in case of errors
    try:
        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_appointments: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        # Verify the veterinarian exists
        veterinarian = Veterinarian.query.get(requesting_vet_id)
        if not veterinarian:
            logger.warning(f"Veterinarian with ID {requesting_vet_id} from token not found (in get_appointments).")
            # 404 is appropriate as the resource (the vet's appointments) effectively doesn't exist for this token.
            return jsonify({"error": f"Veterinarian with ID {requesting_vet_id} not found."}), 404

        logger.info(f"Fetching appointments for veterinarian ID: {requesting_vet_id}")
        appointments = Appointment.query.filter_by(veterinarianId=requesting_vet_id)\
                                        .order_by(Appointment.date.desc())\
                                        .all()

        appointments_list = [{
            "id": appt.id,
            "horseId": appt.horseId,
            "veterinarianId": appt.veterinarianId,
            "date": appt.date.isoformat() if appt.date else None,
            "lamenessRightFront": appt.lamenessRightFront,
            "lamenessLeftFront": appt.lamenessLeftFront,
            "lamenessRightHind": appt.lamenessRightHind,
            "lamenessLeftHind": appt.lamenessLeftHind,
            "BPM": appt.BPM,
            "ECGtime": appt.ECGtime,
            "muscleTensionFrequency": appt.muscleTensionFrequency,
            "muscleTensionStiffness": appt.muscleTensionStiffness,
            "muscleTensionR": appt.muscleTensionR,
            "CBCpath": _get_cbc_url(appt.CBCpath),
            "comment": appt.comment,
        } for appt in appointments]
        return jsonify(appointments_list), 200
    except NotFound as e: # Should be caught if Veterinarian.query.get_or_404 was used, but good to have if direct .get is used.
        logger.warning(f"Not found error in get_appointments (requester from token: {requesting_vet_id_str}): {str(e)}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting appointments for veterinarian (token ID: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@appointments_bp.route('/appointments/horse/<int:horse_id>', methods=['GET'])
@jwt_required()
def get_appointments_by_horse(horse_id):
    """Gets appointments filtered by horse ID from URL."""
    requesting_vet_id_str = None
    try:
        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_appointments_by_horse: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_veterinarian = Veterinarian.query.get(requesting_vet_id)
        if not requesting_veterinarian: # Should ideally not happen if token is valid
            return jsonify({"error": "Authenticated veterinarian not found"}), 404

        horse = Horse.query.get_or_404(horse_id, description=f"Horse with id {horse_id} not found.")

        # Authorization: Check if the requesting vet can view appointments for this horse
        can_access_horse = False
        if horse.veterinarianId == requesting_vet_id:
            can_access_horse = True
        elif requesting_veterinarian.hospitalId is not None and \
             horse.veterinarian and horse.veterinarian.hospitalId == requesting_veterinarian.hospitalId:
            can_access_horse = True

        if not can_access_horse:
            logger.warning(f"Veterinarian {requesting_vet_id} attempt to access appointments for horse {horse_id} without permission.")
            return jsonify({"error": "Forbidden. You do not have permission to view appointments for this horse."}), 403

        appointments = Appointment.query.filter_by(horseId=horse_id).order_by(Appointment.date.desc()).all()

        appointments_list = [{
            "id": appt.id,
            "horseId": appt.horseId,
            "veterinarianId": appt.veterinarianId,
            "date": appt.date.isoformat() if appt.date else None,
            "lamenessRightFront": appt.lamenessRightFront,
            "lamenessLeftFront": appt.lamenessLeftFront,
            "lamenessRightHind": appt.lamenessRightHind,
            "lamenessLeftHind": appt.lamenessLeftHind,
            "BPM": appt.BPM,
            "ECGtime": appt.ECGtime,
            "muscleTensionFrequency": appt.muscleTensionFrequency,
            "muscleTensionStiffness": appt.muscleTensionStiffness,
            "muscleTensionR": appt.muscleTensionR,
            "CBCpath": _get_cbc_url(appt.CBCpath),
            "comment": appt.comment
        } for appt in appointments]
        return jsonify(appointments_list), 200

    except NotFound as e:
         logger.warning(f"Not found error in get_appointments_by_horse (horse_id: {horse_id}, requester: {requesting_vet_id_str}): {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting appointments for horse {horse_id} (requester: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500
    

@appointments_bp.route('/appointments/veterinarian/<int:veterinarian_id>', methods=['GET'])
@jwt_required()
def get_appointments_by_veterinarian(veterinarian_id):
    """Gets appointments filtered by veterinarian ID from URL. Requester must be the veterinarian themselves."""
    requesting_vet_id_str = None
    try:
        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id_from_token = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_appointments_by_veterinarian: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        # Authorization: Vet can only get their own appointments via this specific route
        if veterinarian_id != requesting_vet_id_from_token:
            logger.warning(f"Veterinarian {requesting_vet_id_from_token} attempted to access appointments for veterinarian {veterinarian_id} without permission.")
            return jsonify({"error": "Forbidden. You can only access your own appointments."}), 403

        target_veterinarian = Veterinarian.query.get_or_404(
            veterinarian_id,
            description=f"Veterinarian with id {veterinarian_id} not found."
        )
        appointments = Appointment.query.filter_by(veterinarianId=target_veterinarian.id).order_by(Appointment.date.desc()).all()

        appointments_list = [{
            "id": appt.id,
            "horseId": appt.horseId,
            "veterinarianId": appt.veterinarianId,
            "date": appt.date.isoformat() if appt.date else None,
            "lamenessRightFront": appt.lamenessRightFront,
            "lamenessLeftFront": appt.lamenessLeftFront,
            "lamenessRightHind": appt.lamenessRightHind,
            "lamenessLeftHind": appt.lamenessLeftHind,
            "BPM": appt.BPM,
            "ECGtime": appt.ECGtime,
            "muscleTensionFrequency": appt.muscleTensionFrequency,
            "muscleTensionStiffness": appt.muscleTensionStiffness,
            "muscleTensionR": appt.muscleTensionR,
            "CBCpath": _get_cbc_url(appt.CBCpath),
            "comment": appt.comment
        } for appt in appointments]
        return jsonify(appointments_list), 200

    except NotFound as e:
         logger.warning(f"Not found error in get_appointments_by_veterinarian (vet_id: {veterinarian_id}, requester: {requesting_vet_id_str}): {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting appointments for veterinarian {veterinarian_id} (requester: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500

@appointments_bp.route('/appointment/<int:appointment_id>', methods=['GET'])
@jwt_required()
def get_appointment_by_id(appointment_id):
    """Gets details for a single appointment using the ID from the URL."""
    requesting_vet_id_str = None
    try:
        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_appointment_by_id: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        appointment = Appointment.query.get_or_404(appointment_id, description=f"Appointment with id {appointment_id} not found")

        # Authorization: Check if the requesting vet is assigned to this appointment
        if appointment.veterinarianId != requesting_vet_id:
            logger.warning(
                f"Veterinarian {requesting_vet_id} attempt to access appointment {appointment_id} "
                f"(owned by {appointment.veterinarianId}) without permission.")
            return jsonify({"error": "Forbidden. You can only access your own appointments."}), 403

        return jsonify({
            "id": appointment.id,
            "horseId": appointment.horseId,
            "veterinarianId": appointment.veterinarianId,
            "date": appointment.date.isoformat() if appointment.date else None,
            "lamenessRightFront": appointment.lamenessRightFront,
            "lamenessLeftFront": appointment.lamenessLeftFront,
            "lamenessRightHind": appointment.lamenessRightHind,
            "lamenessLeftHind": appointment.lamenessLeftHind,
            "BPM": appointment.BPM,
            "ECGtime": appointment.ECGtime,
            "muscleTensionFrequency": appointment.muscleTensionFrequency,
            "muscleTensionStiffness": appointment.muscleTensionStiffness,
            "muscleTensionR": appointment.muscleTensionR,
            "CBCpath": _get_cbc_url(appointment.CBCpath),
            "comment": appointment.comment,
        }), 200
    except NotFound as e:
        logger.warning(f"Not found error in get_appointment_by_id (appt_id: {appointment_id}, requester: {requesting_vet_id_str}): {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting appointment {appointment_id} (requester: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@appointments_bp.route('/appointment/<int:appointment_id>', methods=['PUT'])
@jwt_required()
def update_appointment(appointment_id):
    """
    Updates an existing appointment identified by ID in URL.
    Expects multipart/form-data.
    Optional form fields: 'veterinarianId', 'lamenessRightFront', 'lamenessLeftFront',
                          'lamenessRightHind', 'lamenessLeftHind', 'BPM', 'ECGtime',
                          'muscleTensionFrequency', 'muscleTensionStiffness',
                          'muscleTensionR', 'comment'. # noqa: E501
    Optional file upload: 'cbcFile'.
    To remove CBC file, send form field 'remove_cbcFile=true'.
    """
    requesting_vet_id_str = None
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data for PUT.")

        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for update_appointment: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        appointment = Appointment.query.get_or_404(appointment_id, description=f"Appointment with id {appointment_id} not found")

        # Authorization: Vet can only update their own appointments
        if appointment.veterinarianId != requesting_vet_id:
            logger.warning(
                f"Veterinarian {requesting_vet_id} attempt to update appointment {appointment_id} "
                f"(owned by {appointment.veterinarianId}) without permission.")
            return jsonify({"error": "Forbidden. You can only update your own appointments."}), 403

        updated = False

        # VeterinarianId of an appointment is not changed via this endpoint.
        # The appointment remains assigned to the current veterinarian (requesting_vet_id).
        if 'veterinarianId' in request.form:
            new_vet_id_from_form_str = request.form.get('veterinarianId')
            if new_vet_id_from_form_str is not None and new_vet_id_from_form_str.strip() != "":
                try:
                    new_vet_id_from_form = int(new_vet_id_from_form_str)
                    if new_vet_id_from_form != appointment.veterinarianId:
                        # Vet is trying to change assignment, which is not allowed here.
                        raise BadRequest("Cannot change the assigned veterinarian of the appointment via this endpoint.")
                except (ValueError, TypeError):
                    raise BadRequest("Invalid veterinarianId format in form data.")

        if 'comment' in request.form:
            new_comment = request.form.get('comment')
            if appointment.comment != new_comment:
                appointment.comment = new_comment
                updated = True

        if 'BPM' in request.form:
            try:
                new_bpm = request.form.get('BPM', type=int)
                if appointment.BPM != new_bpm:
                    appointment.BPM = new_bpm
                    updated = True
            except (ValueError, TypeError):
                 raise BadRequest("Invalid BPM format, must be an integer.")


        if 'ECGtime' in request.form:
            try:
                new_ecg_time = request.form.get('ECGtime', type=int)
                if appointment.ECGtime != new_ecg_time:
                    appointment.ECGtime = new_ecg_time
                    updated = True
            except (ValueError, TypeError):
                 raise BadRequest("Invalid ECGtime format, must be an integer.")


        cbc_file = request.files.get('cbcFile')
        remove_flag = request.form.get('remove_cbcFile', 'false').lower() == 'true'
        old_cbc_filename = appointment.CBCpath
        new_cbc_filename = None

        if cbc_file:
            logger.info(f"Processing updated CBC file '{cbc_file.filename}' for appointment {appointment_id}")
            try:
                new_cbc_filename = _save_and_convert_cbc(
                    cbc_file, appointment.horseId, appointment.id
                )
                if appointment.CBCpath != new_cbc_filename:
                     appointment.CBCpath = new_cbc_filename
                     updated = True

                if old_cbc_filename and old_cbc_filename != new_cbc_filename:
                    _delete_cbc_pdf(old_cbc_filename)
            except ValueError as e:
                 logger.error(f"Error processing updated CBC file: {e}")
                 raise BadRequest(f"Error processing updated CBC file: {e}")
            except Exception as e:
                 logger.exception("Unexpected error during CBC file update processing.")
                 raise Exception("An unexpected error occurred while processing the updated CBC file.")

        elif remove_flag:
             if old_cbc_filename:
                 logger.info(f"Explicitly removing CBC file for appointment {appointment_id}")
                 if _delete_cbc_pdf(old_cbc_filename):
                     appointment.CBCpath = None
                     updated = True
                 else:
                     logger.warning(f"Could not remove CBC file '{old_cbc_filename}' during update.")


        if not updated:
             return jsonify({"message": "No changes detected for appointment."}), 200

        db.session.commit()
        logger.info(f"Appointment {appointment_id} updated successfully.")


        return jsonify({
             "message": "Appointment updated successfully",
             "appointment": {
                 "id": appointment.id,
                 "horseId": appointment.horseId,
                 "veterinarianId": appointment.veterinarianId,
                 "date": appointment.date.isoformat() if appointment.date else None,
                 "lamenessRightFront": appointment.lamenessRightFront,
                 "lamenessLeftFront": appointment.lamenessLeftFront,
                 "lamenessRightHind": appointment.lamenessRightHind,
                 "lamenessLeftHind": appointment.lamenessLeftHind,
                 "BPM": appointment.BPM,
                 "ECGtime": appointment.ECGtime,
                 "muscleTensionFrequency": appointment.muscleTensionFrequency,
                 "muscleTensionStiffness": appointment.muscleTensionStiffness,
                 "muscleTensionR": appointment.muscleTensionR,
                 "CBCpath": _get_cbc_url(appointment.CBCpath),
                 "comment": appointment.comment
             }
        }), 200

    except (NotFound, BadRequest, UnsupportedMediaType) as e:
        # db.session.rollback() # Not strictly needed here as commit hasn't happened
        logger.warning(f"Client error updating appointment {appointment_id} (requester: {requesting_vet_id_str}): {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error updating appointment {appointment_id} (requester: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@appointments_bp.route('/appointment/<int:appointment_id>', methods=['DELETE'])
@jwt_required()
def delete_appointment(appointment_id):
    """Deletes an appointment and its associated CBC file using ID from URL."""
    requesting_vet_id_str = None
    try:
        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for delete_appointment: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        # Authorization: Vet can only delete their own appointments
        appointment = Appointment.query.get_or_404(appointment_id, description=f"Appointment with id {appointment_id} not found")
        if appointment.veterinarianId != requesting_vet_id:
            logger.warning(
                f"Veterinarian {requesting_vet_id} attempt to delete appointment {appointment_id} "
                f"(owned by {appointment.veterinarianId}) without permission.")
            return jsonify({"error": "Forbidden. You can only delete your own appointments."}), 403
        appointment = Appointment.query.get_or_404(appointment_id, description=f"Appointment with id {appointment_id} not found")

        cbc_filename_to_delete = appointment.CBCpath

        db.session.delete(appointment)
        db.session.commit()
        logger.info(f"Appointment {appointment_id} deleted from database.")


        _delete_cbc_pdf(cbc_filename_to_delete)

        return jsonify({"message": f"Appointment {appointment_id} deleted successfully"}), 200

    except NotFound as e:
         logger.warning(f"Not found error in delete_appointment (appt_id: {appointment_id}, requester: {requesting_vet_id_str}): {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error deleting appointment {appointment_id} (requester: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500
