import logging
from email_validator import EmailNotValidError
from flask import Blueprint, request, jsonify
from email_validator import validate_email, EmailNotValidError
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
import phonenumbers
from lib.models import Veterinarian, db, Hospital
from werkzeug.exceptions import NotFound, BadRequest, UnsupportedMediaType

from lib.routes.hospitals_routes import hospitalToJson

veterinarians_bp = Blueprint('veterinarians', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_veterinarian_details_for_response(veterinarian_id):
    """
    Helper function to fetch and format veterinarian details for a JSON response.
    Does NOT perform authorization checks - assumes the caller has already done so.
    Returns a dictionary or None if the veterinarian is not found.
    """
    veterinarian = Veterinarian.query.get(veterinarian_id)
    if not veterinarian:
        logger.warning(f"Helper function _get_veterinarian_details_for_response: Veterinarian with ID {veterinarian_id} not found.")
        return None

    hospital_data = None
    if veterinarian.hospital:
        hospital_data = hospitalToJson(veterinarian.hospital)

    return {"idVeterinary": veterinarian.id, "name": veterinarian.name, "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber, "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional, "hospital": hospital_data}

@jwt_required()
def add_veterinarian():
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        name = request.form.get('name')
        idCedulaProfissional = request.form.get('idCedulaProfissional')
        email = request.form.get('email')
        phoneNumber = request.form.get('phoneNumber')
        phoneCountryCode = request.form.get('phoneCountryCode')

        if not name or not idCedulaProfissional or name.strip() == "" or str(idCedulaProfissional).strip() == "":
            return jsonify({"error": "Form fields 'name' and 'idCedulaProfissional' are required and cannot be empty"}), 400

        final_email = email if email and email.strip() else None
        final_phone_number = phoneNumber if phoneNumber and phoneNumber.strip() else None
        final_country_code = phoneCountryCode if phoneCountryCode and phoneCountryCode.strip() else None

        if final_phone_number or final_country_code:
             if not final_phone_number or not final_country_code:
                 return jsonify({"error": "Both phoneNumber and phoneCountryCode form fields are required if one is provided"}), 400
             try:
                 full_number = phonenumbers.parse(final_phone_number, final_country_code)
                 if not phonenumbers.is_valid_number(full_number):
                     return jsonify({"error": "Invalid phone number"}), 400
             except phonenumbers.phonenumberutil.NumberParseException:
                 return jsonify({"error": "Invalid phone number format"}), 400
             except Exception as e:
                 return jsonify({"error": f"Phone number validation error: {str(e)}"}), 400
        else:
             final_phone_number = None
             final_country_code = None

        if final_email:
            try:
                validate_email(final_email, check_deliverability=False)
                if Veterinarian.query.filter_by(email=final_email).first():
                    return jsonify({"error": "Veterinarian with this email already exists."}), 409
            except EmailNotValidError as e:
                return jsonify({"error": f"Invalid email format: {str(e)}"}), 400

        veterinarian = Veterinarian(
            name=name.strip(),
            email=final_email,
            phoneNumber=final_phone_number,
            phoneCountryCode=final_country_code,
            idCedulaProfissional=str(idCedulaProfissional).strip()
        )
        db.session.add(veterinarian)
        db.session.commit()
        logger.info(f"Veterinarian added via (commented out) endpoint: ID {veterinarian.id}")

        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional
        }), 201

    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Client error in add_veterinarian (commented out): {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Error adding veterinarian (via commented out endpoint)")
        return jsonify({"error": "An unexpected error occurred"}), 500


@veterinarians_bp.route('/veterinarian', methods=['GET'])
@jwt_required()
def get_current_veterinarian():
    try:
        current_user_id = get_jwt_identity()

        try:
            vet_id = int(current_user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token: {current_user_id}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        veterinarian = Veterinarian.query.get_or_404(
            vet_id,
            description=f"Veterinarian with id {vet_id} not found"
        )

        hospital = veterinarian.hospital
        hospital_data = None
        if hospital:
            hospital_data = hospitalToJson(hospital)

        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional,
            "hospital": hospital_data
        }), 200

    except NotFound as e:
        logger.warning(f"Veterinarian not found for ID from token {current_user_id}: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Error retrieving veterinarian details for ID {current_user_id} from token.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@veterinarians_bp.route('/veterinarian', methods=['PUT'])
@jwt_required()
def update_current_veterinarian():
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("No update data provided in form.")

        current_user_id = get_jwt_identity()
        logger.info(f"Attempting to update veterinarian details for ID from token: {current_user_id} using form data")

        try:
            vet_id = int(current_user_id)
        except (ValueError, TypeError):
             logger.error(f"Invalid identity type in JWT token: {current_user_id}")
             return jsonify({"error": "Invalid user identity in token"}), 401

        veterinarian = Veterinarian.query.get_or_404(vet_id, description=f"Veterinarian with id {vet_id} not found")

        form_data = request.form
        if not form_data:
             logger.warning(f"Update request for vet {vet_id} received empty form data.")
             return jsonify({"message": "No update data provided in form."}), 400

        updated = False

        if 'name' in form_data:
            new_name = form_data.get('name')
            if not new_name or new_name.strip() == "":
                 return jsonify({"error": "Name cannot be empty"}), 400
            if veterinarian.name != new_name.strip():
                veterinarian.name = new_name.strip()
                updated = True

        if 'email' in form_data:
            new_email = form_data.get('email')
            normalized_new_email = None

            # If a new email is provided (not empty string)
            if new_email and new_email.strip():
                try:
                    validated_email_data = validate_email(new_email.strip(), check_deliverability=False)
                    normalized_new_email = validated_email_data.email
                except EmailNotValidError as e:
                    return jsonify({"error": f"Invalid email format: {str(e)}"}), 400
            # If new_email is an empty string or None, normalized_new_email remains None, signifying clearing the email.

            # Only proceed if the normalized new email is different from the current email
            if veterinarian.email != normalized_new_email:
                if normalized_new_email: # If a new, valid, normalized email is to be set
                    try:
                        # Check if this normalized email is already used by ANOTHER veterinarian
                        existing_vet = Veterinarian.query.filter(
                            Veterinarian.email == normalized_new_email,
                            Veterinarian.id != vet_id  # Exclude the current veterinarian
                        ).first()
                        if existing_vet:
                            return jsonify({"error": f"Email '{normalized_new_email}' is already in use by another veterinarian."}), 409
                    except EmailNotValidError as e:
                        return jsonify({"error": f"Invalid email format: {str(e)}"}), 400
                veterinarian.email = normalized_new_email # Store the normalized email or None
                updated = True

        phone_number_updated = False
        if 'phoneNumber' in form_data or 'phoneCountryCode' in form_data:
            new_phone_number = form_data.get('phoneNumber')
            new_country_code = form_data.get('phoneCountryCode')

            final_phone_number = new_phone_number if 'phoneNumber' in form_data else veterinarian.phoneNumber
            final_country_code = new_country_code if 'phoneCountryCode' in form_data else veterinarian.phoneCountryCode

            final_phone_number = final_phone_number if final_phone_number and str(final_phone_number).strip() else None
            final_country_code = final_country_code if final_country_code and str(final_country_code).strip() else None


            if final_phone_number or final_country_code:
                if not final_phone_number or not final_country_code:
                    if ('phoneNumber' in form_data and not final_country_code) or \
                       ('phoneCountryCode' in form_data and not final_phone_number):
                         return jsonify({"error": "Both phoneNumber and phoneCountryCode form fields are required to set/update phone details"}), 400
                    elif (final_phone_number and not final_country_code) or (not final_phone_number and final_country_code):
                         return jsonify({"error": "Both phoneNumber and phoneCountryCode must be provided or both must be cleared"}), 400

                if final_phone_number and final_country_code:
                    try:
                        full_number = phonenumbers.parse(str(final_phone_number), str(final_country_code))
                        if not phonenumbers.is_valid_number(full_number):
                            return jsonify({"error": "Invalid phone number"}), 400
                        if veterinarian.phoneNumber != final_phone_number or veterinarian.phoneCountryCode != final_country_code:
                            veterinarian.phoneNumber = final_phone_number
                            veterinarian.phoneCountryCode = final_country_code
                            phone_number_updated = True
                    except phonenumbers.phonenumberutil.NumberParseException:
                        return jsonify({"error": "Invalid phone number format"}), 400
                    except Exception as e:
                        return jsonify({"error": f"Phone number validation error: {str(e)}"}), 400
            else:
                 if veterinarian.phoneNumber is not None or veterinarian.phoneCountryCode is not None:
                     veterinarian.phoneNumber = None
                     veterinarian.phoneCountryCode = None
                     phone_number_updated = True

        if phone_number_updated:
            updated = True

        if 'idCedulaProfissional' in form_data:
            new_cedula = form_data.get('idCedulaProfissional')
            if new_cedula is None or str(new_cedula).strip() == "":
                 return jsonify({"error": "idCedulaProfissional cannot be empty"}), 400
            if str(veterinarian.idCedulaProfissional) != str(new_cedula).strip():
                veterinarian.idCedulaProfissional = str(new_cedula).strip()
                updated = True

        if 'hospitalId' in form_data:
            hospital_id_str = form_data.get('hospitalId')

            # Standardize input: treat None from form (e.g. ?hospitalId&... ) as empty string
            if hospital_id_str is None:
                hospital_id_str = ""
            else:
                hospital_id_str = hospital_id_str.strip()

            target_hospital_id_for_vet = None # Represents the final state for veterinarian.hospitalId

            if hospital_id_str == "" or hospital_id_str.lower() == "null" or hospital_id_str == "0":
                # User intends to clear the hospital association
                target_hospital_id_for_vet = None
            else:
                # User intends to set/change to a specific hospital
                try:
                    parsed_id = int(hospital_id_str)
                    if parsed_id <= 0: # Assuming 0 is for clearing, handled above.
                        return jsonify({"error": "hospitalId, if provided for assignment, must be a positive integer."}), 400
                    
                    hospital_to_assign = Hospital.query.get(parsed_id)
                    if not hospital_to_assign:
                        return jsonify({"error": f"Hospital with ID {parsed_id} not found."}), 404
                    target_hospital_id_for_vet = parsed_id
                except ValueError:
                    return jsonify({"error": "Invalid hospitalId format. Must be an integer, or empty/null/0 to clear."}), 400
            
            # Apply the change if it's different from the current state
            if veterinarian.hospitalId != target_hospital_id_for_vet:
                veterinarian.hospitalId = target_hospital_id_for_vet
                updated = True

        if not updated:
             relevant_fields_present = any(f in form_data for f in ['name', 'email', 'phoneNumber', 'phoneCountryCode', 'idCedulaProfissional', 'hospitalId'])
             if relevant_fields_present:
                 return jsonify({"message": "No changes detected in the provided veterinarian fields."}), 200
             else:
                 return jsonify({"message": "No relevant update fields provided in form."}), 400


        db.session.commit()
        logger.info(f"Veterinarian {vet_id} updated successfully via form data.")

        hospital_data_for_response = None
        if veterinarian.hospitalId:
            # Accessing veterinarian.hospital will use the SQLAlchemy relationship.
            # It should be up-to-date after the commit or if the session is still active.
            if veterinarian.hospital:
                hospital_data_for_response = hospitalToJson(veterinarian.hospital)

        return jsonify({
            "idVeterinary": veterinarian.id,
            "name": veterinarian.name,
            "email": veterinarian.email,
            "phoneNumber": veterinarian.phoneNumber,
            "phoneCountryCode": veterinarian.phoneCountryCode,
            "idCedulaProfissional": veterinarian.idCedulaProfissional,
            "hospital": hospital_data_for_response
        }), 200

    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except (BadRequest, UnsupportedMediaType) as e:
        logger.warning(f"Client error during veterinarian update: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error updating veterinarian details for ID {current_user_id} from token.")
        return jsonify({"error": "An unexpected error occurred during update"}), 500


@veterinarians_bp.route('/veterinarian', methods = ['DELETE'])
@jwt_required()
def delete_current_veterinarian():
    try:
        current_user_id = get_jwt_identity()
        logger.info(f"Attempting to delete veterinarian for ID from token: {current_user_id}")

        try:
            vet_id = int(current_user_id)
        except (ValueError, TypeError):
             logger.error(f"Invalid identity type in JWT token: {current_user_id}")
             return jsonify({"error": "Invalid user identity in token"}), 401

        veterinarian = Veterinarian.query.get_or_404(vet_id, description=f"Veterinarian with id {vet_id} not found")

        logger.warning(f"Attempting deletion of veterinarian {vet_id}. Related records might be affected by cascade rules.")

        db.session.delete(veterinarian)
        db.session.commit()
        logger.info(f"Veterinarian {vet_id} deleted successfully.")

        return jsonify({"message": "Veterinarian account deleted successfully"}), 200

    except NotFound as e:
         logger.warning(f"Veterinarian not found for deletion, ID from token {current_user_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error deleting veterinarian for ID {current_user_id} from token.")
        return jsonify({"error": "An unexpected error occurred during deletion"}), 500


@veterinarians_bp.route('/veterinarian/<int:target_vet_id>', methods=['GET'])
@jwt_required()
def get_veterinarian_by_id(target_vet_id):
    """
    Retrieves a veterinarian's details by their ID.
    Access is granted if the requester is the veterinarian themselves,
    or if both the requester and the target veterinarian belong to the same hospital.
    """
    requesting_vet_id_str = None # Initialize for broader scope in exception logging
    try:
        requesting_vet_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(requesting_vet_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_veterinarian_by_id: {requesting_vet_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_veterinarian = Veterinarian.query.get_or_404(
            requesting_vet_id,
            description=f"Requesting veterinarian with id {requesting_vet_id} not found. Your token may be invalid or your account may no longer exist."
        )
        target_veterinarian = Veterinarian.query.get_or_404(
            target_vet_id,
            description=f"Target veterinarian with id {target_vet_id} not found."
        )

        # Authorization check
        is_own_profile = (requesting_veterinarian.id == target_veterinarian.id)
        
        can_view_due_to_hospital = False
        if (requesting_veterinarian.hospitalId is not None and \
           target_veterinarian.hospitalId is not None and \
           requesting_veterinarian.hospitalId == target_veterinarian.hospitalId):
            can_view_due_to_hospital = True

        if not (is_own_profile or can_view_due_to_hospital):
            logger.warning(f"Access denied for vet {requesting_veterinarian.id} to view vet {target_veterinarian.id} profile. Own: {is_own_profile}, Same Hospital: {can_view_due_to_hospital}")
            return jsonify({"error": "Access forbidden. You can only view your own profile or profiles of veterinarians in the same hospital."}), 403

        hospital_data = None
        if target_veterinarian.hospital: # Accesses the SQLAlchemy relationship
            hospital_data = hospitalToJson(target_veterinarian.hospital)

        logger.info(f"Veterinarian {requesting_veterinarian.id} successfully accessed profile of veterinarian {target_veterinarian.id}.")
        return jsonify(idVeterinary=target_veterinarian.id, name=target_veterinarian.name, email=target_veterinarian.email, phoneNumber=target_veterinarian.phoneNumber, phoneCountryCode=target_veterinarian.phoneCountryCode, idCedulaProfissional=target_veterinarian.idCedulaProfissional, hospital=hospital_data), 200

    except NotFound as e:
        logger.warning(f"Not found error in get_veterinarian_by_id (target: {target_vet_id}, requester from token: {requesting_vet_id_str}): {str(e)}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Error retrieving veterinarian by ID (target: {target_vet_id}, requester from token: {requesting_vet_id_str}).")
        return jsonify({"error": "An unexpected server error occurred"}), 500
