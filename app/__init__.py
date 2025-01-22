from flask import Flask
from app.config import Config
from app.models import db
from app.routes.clients import clients_bp
from app.routes.horses import horses_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(clients_bp)
    app.register_blueprint(horses_bp)
    
    return app