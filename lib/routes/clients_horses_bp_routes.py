from flask import Blueprint, request, jsonify, url_for
from werkzeug.utils import secure_filename
from lib.models import ClientsHasHorses, db

clients_horses_bp = Blueprint('clients_has_horses', __name__)