import base64
import io
import logging
import os
import random
import uuid
import json
from datetime import datetime
import requests
from flask import Blueprint, jsonify, request, url_for
from flask_jwt_extended import jwt_required
from lib.models import Horse
from PIL import Image, UnidentifiedImageError 
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType, InternalServerError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

xray_bp = Blueprint('xray', __name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATIC_FOLDER_REL = os.path.join('lib', 'static')
XRAY_FOLDER_REL = os.path.join(STATIC_FOLDER_REL, 'xray')


xray_PicturesFolder = os.path.join(project_root, XRAY_FOLDER_REL)


os.makedirs(xray_PicturesFolder, exist_ok=True)

logger.info(f"Xray pictures folder: {xray_PicturesFolder}")



def _get_xray_image_url(filename):
    """Generates the absolute URL for an xray image."""
    if not filename:
        return None
    try:

        relative_path = os.path.join('xray', filename).replace('\\', '/')
        return url_for('static', filename=relative_path, _external=True)
    except RuntimeError as e:
        if 'application context' in str(e).lower():
             logger.error(f"Error generating URL for xray image {filename} due to missing application context. Ensure this runs within a request context.")
        else:
            logger.error(f"Error generating URL for xray image {filename}: {e}")
        return None



def _delete_xray_image(filename):
    """Deletes an xray image file if it exists."""
    if not filename:
        return False
    path = os.path.join(xray_PicturesFolder, filename) # Define path early for logging
    try:
        path = os.path.join(xray_PicturesFolder, filename)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted xray image file: {path}")
            return True
        else:
            logger.warning(f"Attempted to delete non-existent xray image file: {path}")
            return False
    except OSError as e:
        logger.error(f"Error deleting xray image file {path}: {e}")
        return False





@xray_bp.route('/xray', methods=['POST'])
@jwt_required()
def process_xray_and_return_image():
    """
    Receives an X-ray image and horseId, processes it (placeholder),
    and returns the URL of a specific picture ('XRay_Random.png') from the server,
    along with coordinates for its corners (inset by 10px).
    The received image is NOT saved.
    Expects multipart/form-data.
    Required form field: 'horseId'.
    Required file upload: 'picture'.
    """
    try:

        # --- Input Validation ---
        if not request.content_type or 'multipart/form-data' not in request.content_type.lower():
             raise UnsupportedMediaType("Content-Type must be multipart/form-data.")

        horse_id_str = request.form.get('horseId')
        picture_file = request.files.get('picture')

        if not horse_id_str:
            raise BadRequest("'horseId' form field is required.")
        if not picture_file:
            raise BadRequest("Missing 'picture' file upload.")
        if not picture_file.filename:
             raise BadRequest("Received file upload has no filename.")
        try:
            temp_stream = io.BytesIO(picture_file.stream.read())
            picture_file.stream.seek(0)
            with Image.open(temp_stream) as img:
                img.verify() 
            temp_stream.seek(0) 
        except (UnidentifiedImageError, Exception) as img_err: 
            logger.warning(f"Invalid image uploaded: {img_err}")
            raise BadRequest("Invalid or corrupted image file provided.")

        # Validate horseId
        try:
            horse_id = int(horse_id_str)
        except (ValueError, TypeError):
             raise BadRequest("Invalid 'horseId' format. Must be an integer.")

        # Check if horse exists
        if not Horse.query.get(horse_id):
            raise NotFound(f"Horse with id {horse_id} not found.")

        logger.info(f"Received xray image '{secure_filename(picture_file.filename)}' for horse {horse_id}. Processing without saving.")

        # --- Process and Prepare Response ---
        selected_filename = "XRay_Random.png"
        target_file_path = os.path.join(xray_PicturesFolder, selected_filename)

        # Check if the target static image exists
        if not os.path.isfile(target_file_path):
            logger.error(f"Target image file '{selected_filename}' not found in {xray_PicturesFolder}.")
            # Use InternalServerError as this is a server configuration issue
            raise InternalServerError(f"Required reference image '{selected_filename}' not found on server.")

        # Get dimensions of the target image to calculate coordinates
        try:
            with Image.open(target_file_path) as img:
                width, height = img.size
        except (FileNotFoundError, UnidentifiedImageError, Exception) as img_err:
             logger.error(f"Could not open or read target image '{selected_filename}': {img_err}")
             raise InternalServerError(f"Failed to read reference image '{selected_filename}' on server.")


        # Define the coordinates based on image dimensions (inset by 10px)
        inset = 10
        logger.warning(f"Image '{selected_filename}' dimensions ({width}x{height}) are too small for the requested inset ({inset}px). Using edge coordinates.")
        if width <= 2 * inset or height <= 2 * inset:
            tl_x, tl_y = 0, 0
            tr_x, tr_y = width, 0
            bl_x, bl_y = 0, height
            br_x, br_y = width, height
        else:
            tl_x, tl_y = inset, inset
            tr_x, tr_y = width - inset, inset
            bl_x, bl_y = inset, height - inset
            br_x, br_y = width - inset, height - inset

        """ coordinates_data = {
            "Top Left": {"x": tl_x, "y": tl_y, "description": "Top-left corner inset"},
            "Top Right": {"x": tr_x, "y": tr_y, "description": "Top-right corner inset"},
            "Bottom Left": {"x": bl_x, "y": bl_y, "description": "Bottom-left corner inset"},
            "Bottom Right": {"x": br_x, "y": br_y, "description": "Bottom-right corner inset"},
        } """
        
        coordinates_data = {
            "391,52": {"x": 391, "y": 52, "label": "Terceiro osso metacarpiano", "description": "Location of Terceiro osso metacarpiano"},
            "321,141": {"x": 321, "y": 141, "label": "Segundo osso metacarpiano", "description": "Location of Segundo osso metacarpiano"},
            "444,95": {"x": 444, "y": 95, "label": "Quarto osso metacarpiano", "description": "Location of Quarto osso metacarpiano"},
            "352,332": {"x": 352, "y": 332, "label": "Ossos sesamoides proximais", "description": "Location of Ossos sesamoides proximais"}, 
            "455,335": {"x": 455, "y": 335, "label": "Ossos sesamoides proximais", "description": "Location of Ossos sesamoides proximais"},
            "409,621": {"x": 409, "y": 621, "label": "Falange proximal (P1)", "description": "Location of Falange proximal (P1)"},
            "413,903": {"x": 413, "y": 903, "label": "Falange média (P2)", "description": "Location of Falange média (P2)"},
        }

        # Generate URL for the target image
        output_image_url = _get_xray_image_url(selected_filename)
        if not output_image_url:
             # Logged in _get_xray_image_url, raise server error
             raise InternalServerError("Failed to generate URL for the target image.")

        logger.info(f"Coordinates '{coordinates_data}' for horse {horse_id}.")

        # --- Return Success Response ---
        return jsonify({
            "message": "Xray processed.",
            "horseId": horse_id,
            "returnedImageUrl": output_image_url,
            "coordinates_data": coordinates_data # Changed key name for clarity
        }), 200

    # --- Error Handling ---
    except (BadRequest, NotFound, UnsupportedMediaType) as e:
        logger.warning(f"Client error processing xray: {e}")
        return jsonify({"error": str(e.description if hasattr(e, 'description') else e)}), e.code if hasattr(e, 'code') else 400
    except InternalServerError as e:
         # Logged where raised
         return jsonify({"error": str(e.description if hasattr(e, 'description') else e)}), e.code if hasattr(e, 'code') else 500
    except Exception as e:
        logger.exception("Unexpected server error processing xray.")
        return jsonify({"error": "An unexpected server error occurred"}), 500
