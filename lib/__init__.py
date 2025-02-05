from flask import Flask
from lib.config import Config
from lib.models import db
from lib.routes.clients_routes import clients_bp
from lib.routes.horses_routes import horses_bp
from lib.routes.veterinarians_routes import veterinarians_bp
from lib.routes.appointments_routes import appointments_bp
from lib.routes.measures_routes import measures_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(clients_bp)
    app.register_blueprint(horses_bp)
    app.register_blueprint(veterinarians_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(measures_bp)

    return app