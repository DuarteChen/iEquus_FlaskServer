from flask import Flask
from flask_migrate import Migrate
from lib.models import db
from lib.routes.clients_routes import clients_bp
from lib.routes.horses_routes import horses_bp
from lib.routes.veterinarians_routes import veterinarians_bp
from lib.routes.appointments_routes import appointments_bp
from lib.routes.measures_routes import measures_bp

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:a22203153@localhost/iEquusDB'
    #app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:a22203153@iEquus-mysql/iEquusDB' # to use with docker


    db.init_app(app)

    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(clients_bp)
    app.register_blueprint(horses_bp)
    app.register_blueprint(veterinarians_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(measures_bp)

    return app