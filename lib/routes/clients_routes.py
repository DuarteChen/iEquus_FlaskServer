import logging
from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from lib.models import Client, ClientHorse, Horse, db, Veterinarian
import phonenumbers
from email_validator import validate_email, EmailNotValidError

from lib.routes.horses_routes import _get_image_url # For consistent image URL generation
from sqlalchemy import distinct

from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

clients_bp = Blueprint('clients', __name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _can_vet_access_client(requesting_vet: Veterinarian, client_to_check: Client) -> bool:
    """
    Checks if the requesting veterinarian can access the details of a specific client.
    Access is granted if the client is associated with any horse that the vet
    can access (either their own or one from their hospital).
    """
    # Find all horses associated with this client
    client_horse_associations = ClientHorse.query.filter_by(clientId=client_to_check.id).all()
    if not client_horse_associations:
        # If client has no horses, they are not accessible via horse-vet linkage by default.
        # Modify this if "orphan" clients should be accessible under different rules.
        return False

    for assoc in client_horse_associations:
        horse = Horse.query.get(assoc.horseId)
        if not horse: # Should not happen in a consistent DB
            continue

        # Check 1: Is it the vet's own horse?
        if horse.veterinarianId == requesting_vet.id:
            return True

        # Check 2: Is it a horse from the vet's hospital?
        if requesting_vet.hospitalId is not None and \
           horse.veterinarian is not None and \
           horse.veterinarian.hospitalId == requesting_vet.hospitalId:
            return True
            
    return False

@clients_bp.route('/client', methods=['POST'])
@jwt_required()
def add_client():
    """
    Adds a new client. Expects multipart/form-data.
    Required form field: 'name'.
    Optional form fields: 'email', 'phoneNumber', 'phoneCountryCode'.
    If 'phoneNumber' is provided, 'phoneCountryCode' is also required.
    """
    try:

        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")


        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phoneNumber')
        phone_country_code = request.form.get('phoneCountryCode')

        if not name or name.strip() == "":
            raise BadRequest("Client name form field is required and cannot be empty.")


        if phone_number or phone_country_code:
            if not phone_number or not phone_country_code:
                raise BadRequest("Both phoneNumber and phoneCountryCode form fields are required if one is provided.")
            try:
                full_number = phonenumbers.parse(phone_number, phone_country_code)
                if not phonenumbers.is_valid_number(full_number):
                    raise BadRequest("Invalid phone number.")
            except phonenumbers.phonenumberutil.NumberParseException:
                raise BadRequest("Invalid phone number format.")
            except Exception as e:
                logger.error(f"Phone number validation error: {e}")
                raise BadRequest(f"Phone number validation error: {str(e)}")


        if email:
            try:
                validate_email(email, check_deliverability=False)
            except EmailNotValidError as e:
                raise BadRequest(f"Invalid email format: {str(e)}")



        client = Client(
            name=name,
            phoneNumber=phone_number,
            phoneCountryCode=phone_country_code,
            email=email
        )
        db.session.add(client)
        db.session.commit()
        logger.info(f"Client created with ID: {client.id}")


        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode,
            "email": client.email
        }), 201

    except (BadRequest, NotFound, UnsupportedMediaType) as e:
        db.session.rollback()
        logger.warning(f"Client error adding client: {e}")
        return jsonify({"error": str(e)}), e.code if hasattr(e, 'code') else 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Server error adding client.")
        return jsonify({"error": "An unexpected server error occurred"}), 500


@clients_bp.route('/clients', methods=['GET'])
@jwt_required()
def get_clients():
    """
    Gets a list of clients accessible to the requesting veterinarian.
    A client is accessible if they are associated with a horse managed by the vet
    or by any vet in the vet's hospital.
    """
    try:
        current_user_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(current_user_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_clients: {current_user_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_vet = Veterinarian.query.get(requesting_vet_id)
        if not requesting_vet:
            logger.warning(f"Veterinarian with ID {requesting_vet_id} from token not found (in get_clients).")
            return jsonify({"error": "Authenticated veterinarian not found"}), 404

        accessible_horse_ids = set()
        if requesting_vet.hospitalId:
            # Vet has a hospital, get all horses from all vets in that hospital
            vets_in_hospital_query = Veterinarian.query.filter_by(hospitalId=requesting_vet.hospitalId).with_entities(Veterinarian.id)
            vet_ids_in_hospital = {v[0] for v in vets_in_hospital_query.all()}
            
            hospital_horses_query = Horse.query.filter(Horse.veterinarianId.in_(list(vet_ids_in_hospital))).with_entities(Horse.id)
            accessible_horse_ids.update(h[0] for h in hospital_horses_query.all())
        else:
            # Only vet's own horses
            own_horses_query = Horse.query.filter_by(veterinarianId=requesting_vet.id).with_entities(Horse.id)
            accessible_horse_ids.update(h[0] for h in own_horses_query.all())

        if not accessible_horse_ids:
            return jsonify([]), 200 # No accessible horses, so no accessible clients via this logic

        # Find client_ids associated with these accessible_horse_ids
        client_ids_query = db.session.query(distinct(ClientHorse.clientId)).filter(ClientHorse.horseId.in_(list(accessible_horse_ids)))
        accessible_client_ids = {c[0] for c in client_ids_query.all()}

        clients = Client.query.filter(Client.id.in_(list(accessible_client_ids))).order_by(Client.name).all()
        
        clients_list = [{
            "idClient": client.id,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode
        } for client in clients]
        return jsonify(clients_list), 200

    except Exception as e:
        logger.exception(f"Server error getting clients for vet {current_user_id_str}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@clients_bp.route('/client/<int:client_id>', methods=['GET'])
@jwt_required()
def get_client_by_id(client_id):
    """
    Gets details for a single client if accessible to the requesting veterinarian.
    """
    current_user_id_str = None
    try:
        current_user_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(current_user_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_client_by_id: {current_user_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_vet = Veterinarian.query.get(requesting_vet_id)
        if not requesting_vet: # Should not happen with a valid token usually
            return jsonify({"error": "Authenticated veterinarian not found"}), 404

        client = Client.query.get_or_404(client_id, description=f"Client with id {client_id} not found.")

        if not _can_vet_access_client(requesting_vet, client):
            logger.warning(f"Veterinarian {requesting_vet_id} attempt to access client {client_id} without permission.")
            return jsonify({"error": f"Client with id {client_id} not found or access denied."}), 404

        return jsonify({
                "idClient": client.id,
                "name": client.name,
                "email": client.email,
                "phoneNumber": client.phoneNumber,
                "phoneCountryCode": client.phoneCountryCode
            }), 200
    except NotFound as e:
         return jsonify({"error": str(e)}), 404
    except Exception as e: # Catch any other unexpected errors
        logger.exception(f"Server error getting client {client_id} for vet {current_user_id_str}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@clients_bp.route('/client/<int:client_id>', methods=['PUT'])
@jwt_required()
def update_client(client_id):
    """
    Handles PUT for a single client identified by ID in URL.
    Expects multipart/form-data:
        - 'name' (optional form field)
        - 'email' (optional form field)
        - 'phoneNumber' (optional form field)
        - 'phoneCountryCode' (optional form field)
    """
    current_user_id_str = None
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data for PUT.")

        current_user_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(current_user_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for update_client: {current_user_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_vet = Veterinarian.query.get(requesting_vet_id)
        if not requesting_vet:
            return jsonify({"error": "Authenticated veterinarian not found"}), 404

        client = Client.query.get_or_404(client_id, description=f"Client with id {client_id} not found.")
        
        if not _can_vet_access_client(requesting_vet, client):
            logger.warning(f"Veterinarian {requesting_vet_id} attempt to update client {client_id} without permission.")
            return jsonify({"error": f"Client with id {client_id} not found or access denied."}), 404
        updated = False


        if 'name' in request.form:
            new_name = request.form.get('name')
            if not new_name or new_name.strip() == "":
                 raise BadRequest("Client name cannot be empty.")
            if client.name != new_name:
                client.name = new_name
                updated = True


        if 'email' in request.form:
            new_email = request.form.get('email')

            if client.email != new_email:
                if new_email and new_email.strip() != "":
                    try:
                        validate_email(new_email, check_deliverability=False)

                    except EmailNotValidError as e:
                        raise BadRequest(f"Invalid email format: {str(e)}")
                    client.email = new_email
                else:
                    client.email = None
                updated = True


        phone_updated = False
        if 'phoneNumber' in request.form or 'phoneCountryCode' in request.form:
            new_phone_number = request.form.get('phoneNumber')
            new_country_code = request.form.get('phoneCountryCode')


            final_phone_number = new_phone_number if 'phoneNumber' in request.form else client.phoneNumber
            final_country_code = new_country_code if 'phoneCountryCode' in request.form else client.phoneCountryCode


            if final_phone_number or final_country_code:
                if not final_phone_number or not final_country_code:
                    raise BadRequest("Both phoneNumber and phoneCountryCode are required to update phone details.")
                try:
                    full_number = phonenumbers.parse(final_phone_number, final_country_code)
                    if not phonenumbers.is_valid_number(full_number):
                        raise BadRequest("Invalid phone number.")

                    if client.phoneNumber != final_phone_number or client.phoneCountryCode != final_country_code:
                        client.phoneNumber = final_phone_number
                        client.phoneCountryCode = final_country_code
                        phone_updated = True
                except phonenumbers.phonenumberutil.NumberParseException:
                    raise BadRequest("Invalid phone number format.")
                except Exception as e:
                    logger.error(f"Phone number validation error during update: {e}")
                    raise BadRequest(f"Phone number validation error: {str(e)}")
            else:
                if client.phoneNumber is not None or client.phoneCountryCode is not None:
                    client.phoneNumber = None
                    client.phoneCountryCode = None
                    phone_updated = True

        if phone_updated:
            updated = True

        if not updated:
            return jsonify({"message": "No fields provided or values unchanged."}), 200

        db.session.commit()
        logger.info(f"Client {client_id} updated.")

        return jsonify({
            "idClient": client.id,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode
        }), 200

    except (NotFound, BadRequest, UnsupportedMediaType) as e:
         db.session.rollback()
         logger.warning(f"Client error updating client {client_id}: {e}")
         return jsonify({"error": str(e)}), getattr(e, 'code', 400)
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error updating client {client_id} by vet {current_user_id_str}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@clients_bp.route('/client/<int:client_id>', methods=['DELETE'])
@jwt_required()
def delete_client(client_id):
    """Deletes a client if accessible to the requesting veterinarian."""
    current_user_id_str = None
    try:
        current_user_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(current_user_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for delete_client: {current_user_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_vet = Veterinarian.query.get(requesting_vet_id)
        if not requesting_vet:
            return jsonify({"error": "Authenticated veterinarian not found"}), 404

        client = Client.query.get_or_404(client_id, description=f"Client with id {client_id} not found.")

        if not _can_vet_access_client(requesting_vet, client):
            logger.warning(f"Veterinarian {requesting_vet_id} attempt to delete client {client_id} without permission.")
            return jsonify({"error": f"Client with id {client_id} not found or access denied."}), 404
        db.session.delete(client)
        db.session.commit()
        logger.info(f"Client {client_id} deleted.")
        return jsonify({"message": "Client deleted successfully"}), 200

    except NotFound as e:
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error deleting client {client_id} by vet {current_user_id_str}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@clients_bp.route('/client/<int:client_id>/horse', methods=['POST', 'PUT', 'DELETE'])
@jwt_required()
def handle_client_horse_association(client_id):
    """
    Handles associating (POST), updating (PUT), or removing (DELETE) a horse
    from a client identified by ID in URL.
    Expects multipart/form-data:
    POST/PUT: 'horseId' (required), 'isClientHorseOwner' (required, 'true'/'false')
    DELETE: 'horseId' (required)
    """
    current_user_id_str = None
    try:
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        current_user_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(current_user_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for handle_client_horse_association: {current_user_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401
        
        requesting_vet = Veterinarian.query.get(requesting_vet_id)
        if not requesting_vet: return jsonify({"error": "Authenticated veterinarian not found"}), 404

        horse_id_str = request.form.get('horseId')
        try:
            if horse_id_str is None: raise ValueError("'horseId' form field is required.")
            horse_id = int(horse_id_str)
        except (ValueError, TypeError):
             raise BadRequest("Invalid or missing 'horseId' form field.")


        client = Client.query.get_or_404(client_id, description=f"Client with id {client_id} not found.")
        horse = Horse.query.get_or_404(horse_id, description=f"Horse with id {horse_id} not found.")

        # Authorization: Vet must have access to the HORSE to manage its client associations
        can_manage_horse = False
        if horse.veterinarianId == requesting_vet.id:
            can_manage_horse = True
        elif requesting_vet.hospitalId is not None and \
             horse.veterinarian and \
             horse.veterinarian.hospitalId == requesting_vet.hospitalId:
            can_manage_horse = True

        if not can_manage_horse:
            logger.warning(
                f"Veterinarian {requesting_vet.id} attempt to manage client associations "
                f"for horse {horse_id} (client {client_id}) without permission for the horse."
            )
            # Obscure by saying horse not found, consistent with horses_routes.py
            return jsonify({"error": f"Horse with id {horse_id} not found or access denied."}), 404


        existing_relation = ClientHorse.query.filter_by(clientId=client_id, horseId=horse_id).first()


        if request.method == 'POST':
            if existing_relation:
                raise BadRequest("Client already associated with this horse.", 409)

            is_owner_str = request.form.get('isClientHorseOwner')
            if is_owner_str is None:
                 raise BadRequest("'isClientHorseOwner' form field is required.")

            is_owner = is_owner_str.lower() == 'true'

            client_horse_relation = ClientHorse(clientId=client_id, horseId=horse_id, isClientHorseOwner=is_owner)
            db.session.add(client_horse_relation)
            db.session.commit()
            logger.info(f"Associated horse {horse_id} with client {client_id} (Owner: {is_owner}).")
            return jsonify({"message": "Horse successfully associated with client"}), 201


        elif request.method == 'PUT':
            if not existing_relation:
                raise NotFound("Client is not associated with this horse.")

            is_owner_str = request.form.get('isClientHorseOwner')
            if is_owner_str is None:
                 raise BadRequest("'isClientHorseOwner' form field is required for update.")
            is_owner = is_owner_str.lower() == 'true'

            if existing_relation.isClientHorseOwner != is_owner:
                existing_relation.isClientHorseOwner = is_owner
                db.session.commit()
                logger.info(f"Updated association for horse {horse_id} and client {client_id} (Owner: {is_owner}).")
                return jsonify({"message": "Horse's relation with client successfully updated"}), 200
            else:
                return jsonify({"message": "No change in ownership status."}), 200


        elif request.method == 'DELETE':
            if not existing_relation:
                raise NotFound("Client is not associated with this horse.")

            db.session.delete(existing_relation)
            db.session.commit()
            logger.info(f"Removed association between horse {horse_id} and client {client_id}.")
            return jsonify({"message": "Horse successfully removed from client"}), 200

    except (NotFound, BadRequest, UnsupportedMediaType) as e:
         db.session.rollback()
         logger.warning(f"Client error handling client-horse association for client {client_id}: {e}")
         return jsonify({"error": str(e)}), getattr(e, 'code', 400)
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Server error handling client-horse association for client {client_id} by vet {current_user_id_str}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500



@clients_bp.route('/client/<int:client_id>/horses', methods=['GET'])
@jwt_required()
def get_client_horses(client_id):
    """
    Gets the list of horses associated with a specific client,
    identified by the ID in the URL path.
    """
    current_user_id_str = None
    try:
        current_user_id_str = get_jwt_identity()
        try:
            requesting_vet_id = int(current_user_id_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid identity type in JWT token for get_client_horses: {current_user_id_str}")
            return jsonify({"error": "Invalid user identity in token"}), 401

        requesting_vet = Veterinarian.query.get(requesting_vet_id)
        if not requesting_vet: return jsonify({"error": "Authenticated veterinarian not found"}), 404
        
        client = Client.query.get_or_404(client_id, description=f"Client with id {client_id} not found.")

        if not _can_vet_access_client(requesting_vet, client):
            logger.warning(f"Veterinarian {requesting_vet_id} attempt to get horses for client {client_id} without permission for the client.")
            return jsonify({"error": f"Client with id {client_id} not found or access denied."}), 404
        horses_list = []

        associations = ClientHorse.query.filter_by(clientId=client_id).all()
        for assoc in associations:
            horse = Horse.query.get(assoc.horseId)
        
            # Only include horses the vet can access, although the primary check is on the client
            if horse and (_can_vet_access_client(requesting_vet, client)): # Redundant check, but safe
                horses_list.append({
                    "idHorse": horse.id,
                    "name": horse.name,
                    "isOwner": assoc.isClientHorseOwner
                })

        return jsonify(horses_list), 200

    except NotFound as e:

         logger.warning(f"Client error getting horses for client {client_id}: {e}")
         return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"Server error getting horses for client {client_id} by vet {current_user_id_str}.")
        return jsonify({"error": "An unexpected server error occurred"}), 500
