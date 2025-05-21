from email_validator import EmailNotValidError
from flask import Blueprint, request, jsonify
from email_validator import validate_email, EmailNotValidError
from zxcvbn import zxcvbn
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
import phonenumbers
from lib.models import Veterinarian, db, Hospital 
from werkzeug.exceptions import NotFound, BadRequest, UnsupportedMediaType
import requests # For calling the predict service
from sqlalchemy.exc import SQLAlchemyError # For DB connection errors

import logging # Import standard logging


login_bp = Blueprint('login', __name__)
logger = logging.getLogger(__name__) # Correct logger setup

@login_bp.route('/register', methods=['POST'])
def register_veterinarian():
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.") # Use correct exception

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        idCedulaProfissional = request.form.get('idCedulaProfissional')
        phoneNumber = request.form.get('phoneNumber')
        phoneCountryCode = request.form.get('phoneCountryCode')
        hospital_id_str = request.form.get('hospitalId')

        hospitalId_int = None # Default to None if not provided or invalid
        if hospital_id_str and hospital_id_str.strip():
            try:
                hospitalId_int = int(hospital_id_str)
                if not Hospital.query.get(hospitalId_int):
                    return jsonify({"error": f"Hospital with id {hospitalId_int} not found."}), 404
            except ValueError:
                return jsonify({"error": "Invalid hospitalId format. Must be an integer."}), 400
        # If hospital_id_str is empty or not provided, hospitalId_int remains None, which is now allowed.

        required_fields = {'name': name, 'email': email, 'password': password}
        missing_or_empty_fields = [key for key, value in required_fields.items() if not value or str(value).strip() == ""]
        if missing_or_empty_fields:
            return jsonify({"error": f"Missing or empty required form fields."}), 400

        # Validate and normalize the email
        try:
            # The result of validate_email is an object containing the normalized email.
            validated_email_data = validate_email(email.strip(), check_deliverability=False)
            normalized_email = validated_email_data.email # .email attribute holds the normalized form
        except EmailNotValidError as e:
            return jsonify({"error": f"Invalid email format."}), 400

        # Check if a veterinarian with this normalized email already exists
        existing_veterinarian = Veterinarian.query.filter_by(email=normalized_email).first()
        if existing_veterinarian is not None:
            return jsonify({"error": "Veterinarian with this email already exists."}), 409
        result = zxcvbn(password) 
        #biblioteca do dropbox para verificação de passwords - source ChatGPT
        ''''
            TODO - Verificar no front as condições
        	•	Uppercase letters (A–Z)
            •	Lowercase letters (a–z)
            •	Digits (0–9)
            •	Symbols (!@#$%^&*() etc.)
        '''
        if result['score'] < 2:
            return jsonify({"error": "Password must be stronger."}), 400

        final_phone_number = phoneNumber if phoneNumber and str(phoneNumber).strip() else None
        final_country_code = phoneCountryCode if phoneCountryCode and str(phoneCountryCode).strip() else None

        if final_phone_number or final_country_code:
             if not final_phone_number or not final_country_code:
                 return jsonify({"error": "Both phoneNumber and phoneCountryCode form fields are required if one is provided"}), 400
             try:
                full_number = phonenumbers.parse(str(final_phone_number), str(final_country_code))
                if not phonenumbers.is_valid_number(full_number):
                    logger.warning(f"Invalid phone number provided during registration: {final_country_code}{final_phone_number}")
                    return jsonify({"error": "Invalid phone number"}), 400
             except phonenumbers.phonenumberutil.NumberParseException as e:
                logger.warning(f"Phone number parsing error during registration: {e}")
                return jsonify({"error": "Invalid phone number format"}), 400
             except Exception as e:
                logger.error(f"Unexpected phone number validation error during registration: {e}")
                return jsonify({"error": f"Phone number validation error."}), 400
        else:
             final_phone_number = None
             final_country_code = None

        veterinarian = Veterinarian(
            name=name.strip(),
            email=normalized_email, # Store the normalized email
            phoneNumber=final_phone_number,
            phoneCountryCode=final_country_code,
            idCedulaProfissional=str(idCedulaProfissional).strip() if idCedulaProfissional else None,
            hospitalId=hospitalId_int # Use the validated integer hospitalId
        )
        veterinarian.set_password(password)

        db.session.add(veterinarian)
        db.session.commit()
        logger.info(f"Veterinarian registered successfully with ID: {veterinarian.id}")

        return jsonify({
            "message": "Veterinarian registered successfully.",
            "veterinarian": {
                "id": veterinarian.id,
                "name": veterinarian.name,
                "email": veterinarian.email,
                "idCedulaProfissional": veterinarian.idCedulaProfissional,
                "phoneNumber": veterinarian.phoneNumber,
                "phoneCountryCode": veterinarian.phoneCountryCode,
                "hospitalId": veterinarian.hospitalId
            }
        }), 201

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Client error during registration: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Server error during veterinarian registration.")
        return jsonify({"error": "An unexpected error occurred during registration."}), 500


@login_bp.route('/login', methods=['POST'])
def login_veterinarian():
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        email_input = request.form.get('email')
        password = request.form.get('password').strip()

        if not email_input or not password or email_input.strip() == "" or password.strip() == "":
            logger.warning("Login attempt failed: Missing or empty email or password from %s", request.remote_addr)
            return jsonify({"error": "Email and password form fields are required and cannot be empty"}), 400

        try:
            validated_email_data = validate_email(email_input.strip(), check_deliverability=False)
            normalized_email = validated_email_data.email
        except EmailNotValidError as e:
            logger.warning("Login attempt failed: Invalid email format '%s' from %s", email_input, request.remote_addr)
            return jsonify({"error": "Invalid credentials"}), 401

        veterinarian = Veterinarian.query.filter_by(email=normalized_email).first()

        if veterinarian and veterinarian.check_password(password):
            access_token = create_access_token(identity=str(veterinarian.id))
            logger.info("Successful login for veterinarian ID: %s", veterinarian.id)
            return jsonify(access_token=access_token), 200
        else:
            logger.warning("Login attempt failed: Invalid credentials for email '%s' from %s", normalized_email, request.remote_addr)
            return jsonify({"error": "Invalid credentials"}), 401

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Client error during login: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        logger.exception("Unexpected server error during login attempt.")
        return jsonify({"error": "An unexpected server error occurred during login"}), 500


@login_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        current_user_id = get_jwt_identity()
        logger.info(f"Attempting password change for veterinarian ID: {current_user_id}")

        try:
            vet_id = int(current_user_id)
        except (ValueError, TypeError):
             logger.error(f"Invalid identity type in JWT token during password change: {current_user_id}")
             return jsonify({"error": "Invalid user identity in token"}), 401

        veterinarian = Veterinarian.query.get_or_404(vet_id, description="Veterinarian not found")
        old_password = request.form.get('old_password').strip()
        new_password = request.form.get('new_password').strip()

        if not old_password or not new_password or old_password.strip() == "" or new_password.strip() == "":
            return jsonify({"error": "Form fields 'old_password' and 'new_password' are required and cannot be empty"}), 400

        if not veterinarian.check_password(old_password):
            logger.warning(f"Incorrect old password provided for veterinarian ID: {vet_id}")
            return jsonify({"error": "Incorrect old password"}), 400

        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters long"}), 400

        if old_password == new_password:
             return jsonify({"error": "New password cannot be the same as the old password"}), 400

        veterinarian.set_password(new_password)
        db.session.commit()
        logger.info(f"Password changed successfully for veterinarian ID: {vet_id}")

        return jsonify({"message": "Password changed successfully"}), 200

    except NotFound as e:
         logger.warning(f"Veterinarian not found for password change, ID from token {current_user_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Client error during password change: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error changing password for veterinarian ID {current_user_id}.")
        return jsonify({"error": "An unexpected error occurred changing password"}), 500


@login_bp.route('/health')
def health_check():
    predict_service_url = "http://iequus_predict:9091/health" # As defined in docker-compose and predict app
    status = {
        "database": "unavailable",
        "predict_service": "unavailable",
        "overall_status": "unhealthy"
    }
    http_status_code = 503  # Service Unavailable by default
    
    # Check database connectivity
    try:
        db.session.execute(db.text('SELECT 1'))
        status["database"] = "ok"
        logger.debug("Health check: Database connection successful.")
    except SQLAlchemyError as e:
        logger.error(f"Health check: Database connection error: {e}")
        status["database"] = f"error - {type(e).__name__}"
    except Exception as e:
        logger.error(f"Health check: Unexpected error during database check: {e}")
        status["database"] = f"unexpected error - {type(e).__name__}"
        
    # Check predict service connectivity
    try:
        response = requests.get(predict_service_url, timeout=5) # 5 second timeout
        if response.status_code == 200 and response.text.strip().upper() == "OK":
            status["predict_service"] = "ok"
            logger.debug("Health check: Predict service connection successful.")
        else:
            status["predict_service"] = f"error - status code {response.status_code}"
            logger.warning(f"Health check: Predict service returned status {response.status_code}, content: {response.text[:100]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Health check: Predict service connection error: {e}")
        status["predict_service"] = f"error - {type(e).__name__}"

    if status["database"] == "ok" and status["predict_service"] == "ok":
        status["overall_status"] = "healthy"
        http_status_code = 200



    return jsonify(status), http_status_code
