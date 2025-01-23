from flask import Flask
from app.config import Config
from app.models import db
from app.routes.clients_routes import clients_bp
from app.routes.horses_routes import horses_bp
from app.routes.veterinarians_routes import veterinarians_bp
from app.routes.appointments_routes import appointments_bp
from app.routes.measures_routes import measures_bp
from app.routes.pictures_routes import pictures_bp
from app.routes.cbc_routes import cbc_bp
#from app.routes.clients_horses_bp_routes import clients_horses_bp_bp 

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
    app.register_blueprint(pictures_bp)
    app.register_blueprint(cbc_bp)
    #app.register_blueprint(clients_horses_bp)
    
    return app