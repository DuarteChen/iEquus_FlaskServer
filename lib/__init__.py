from datetime import timedelta
import os
from flask import Flask
from dotenv import load_dotenv
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from lib.models import db
from lib.routes.clients_routes import clients_bp
from lib.routes.horses_routes import horses_bp
from lib.routes.veterinarians_routes import veterinarians_bp
from lib.routes.appointments_routes import appointments_bp
from lib.routes.measures_routes import measures_bp
from lib.routes.xray_routes import xray_bp
from lib.routes.login_routes import login_bp
from lib.routes.hospitals_routes import hospitals_bp

load_dotenv()

bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)

    # Initialize Bcrypt with the app
    bcrypt.init_app(app)

    CORS(app)

    # Carregar configurações do .env
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")    
    #DATABASE_URL = os.getenv("DATABASE_URL")
    DATABASE_URL = "mysql+pymysql://root:flutter_app_db@127.0.0.1/iEquusDB"

    # Configurar a aplicação Flask
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=730) #Para não estar sempre a fazer login, o token tem validade de 2 anos
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['JWT_ALGORITHM'] = 'HS256'

    # Inicializar banco de dados
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Registrar blueprints
    app.register_blueprint(clients_bp)
    app.register_blueprint(horses_bp)
    app.register_blueprint(veterinarians_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(measures_bp)
    app.register_blueprint(xray_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(hospitals_bp)

    # Inicializar JWT

    jwt = JWTManager(app)

    return app