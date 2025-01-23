from flask import Blueprint, request, jsonify
from app.models import Picture, db

pictures_bp = Blueprint('pictures', __name__)

@pictures_bp.route('/pictures', methods=['POST'])
def add_picture():
    try:
        data = request.get_json()
        if 'measureID' not in data or 'path' not in data or 'date' not in data:
            return jsonify({"error": "measureID, path, and date are required"}), 400
        
        picture = Picture(
            measure_id=data['measureID'],
            path=data['path'],
            date=data['date']
        )
        db.session.add(picture)
        db.session.commit()
        
        return jsonify({
            "idPicture": picture.id,
            "measureID": picture.measure_id,
            "path": picture.path,
            "date": picture.date
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pictures_bp.route('/pictures', methods=['GET'])
def get_pictures():
    try:
        pictures = Picture.query.all()
        pictures_list = [{
            "idPicture": pic.id,
            "measureID": pic.measure_id,
            "path": pic.path,
            "date": pic.date
        } for pic in pictures]
        
        return jsonify(pictures_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500