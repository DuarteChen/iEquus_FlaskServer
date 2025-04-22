from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func

bcrypt = Bcrypt()
db = SQLAlchemy()

class Horse(db.Model):
    __tablename__ = 'Horses'

    id = db.Column('idHorse', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    profilePicturePath = db.Column(db.String(255), nullable=True)
    birthDate = db.Column(db.DateTime, nullable=True)
    pictureRightFrontPath = db.Column(db.String(255), nullable=True)
    pictureLeftFrontPath = db.Column(db.String(255), nullable=True)
    pictureRightHindPath = db.Column(db.String(255), nullable=True)
    pictureLeftHindPath = db.Column(db.String(255), nullable=True)

    appointments = db.relationship('Appointment', backref='horse', cascade="all, delete-orphan")
    measures = db.relationship('Measure', backref='horse', cascade="all, delete-orphan")
    clients = db.relationship('Client', secondary='Clients_has_horses', back_populates='horses')

class Veterinarian(db.Model):
    __tablename__ = 'Veterinarians'

    id = db.Column('idVeterinarian', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=False)
    phoneNumber = db.Column(db.String(20), nullable=True)
    phoneCountryCode = db.Column(db.String(10), nullable=True)
    password = db.Column(db.String(255), nullable=True)
    idCedulaProfissional = db.Column(db.String(40), nullable=False)

    appointments = db.relationship('Appointment', backref='veterinarian', cascade="all, delete-orphan")
    measures = db.relationship('Measure', backref='veterinarian', cascade="all, delete-orphan")

    def set_password(self, password):
        if password:
            self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        else:
            self.password = None

    def check_password(self, password):
        if not self.password or not password:
            return False
        return bcrypt.check_password_hash(self.password, password)

class Appointment(db.Model):
    __tablename__ = 'Appointments'

    id = db.Column('idAppointment', db.Integer, primary_key=True, autoincrement=True)
    horseId = db.Column(db.Integer, db.ForeignKey('Horses.idHorse'), nullable=False)
    veterinarianId = db.Column(db.Integer, db.ForeignKey('Veterinarians.idVeterinarian'), nullable=False)
    lamenessRightFront = db.Column(db.Integer, nullable=True)
    lamenessLeftFront = db.Column(db.Integer, nullable=True)
    lamenessRightHind = db.Column(db.Integer, nullable=True)
    lamenessLeftHind = db.Column(db.Integer, nullable=True)
    BPM = db.Column(db.Integer, nullable=True)
    muscleTensionFrequency = db.Column(db.String(255), nullable=True)
    muscleTensionStiffness = db.Column(db.String(255), nullable=True)
    muscleTensionR = db.Column(db.String(255), nullable=True)
    CBCpath = db.Column(db.String(255), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False, server_default=func.now())
    ECGtime = db.Column(db.Integer, nullable=True)

    measures = db.relationship('Measure', backref='appointment', cascade="all, delete-orphan")

class Client(db.Model):
    __tablename__ = 'Clients'

    id = db.Column('idClient', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(20), nullable=True)
    phoneCountryCode = db.Column(db.String(10), nullable=True)

    horses = db.relationship('Horse', secondary='Clients_has_horses', back_populates='clients')

class ClientHorse(db.Model):
    __tablename__ = 'Clients_has_horses'

    clientId = db.Column('Clients_idClient', db.Integer, db.ForeignKey('Clients.idClient'), primary_key=True)
    horseId = db.Column('horses_idHorse', db.Integer, db.ForeignKey('Horses.idHorse'), primary_key=True)
    isClientHorseOwner = db.Column(db.Boolean, nullable=False)

class Measure(db.Model):
    __tablename__ = 'Measures'

    id = db.Column('idMeasure', db.Integer, primary_key=True, autoincrement=True)
    userBW = db.Column(db.Integer, nullable=True)
    algorithmBW = db.Column(db.Integer, nullable=True)
    userBCS = db.Column(db.Integer, nullable=True)
    algorithmBCS = db.Column(db.Integer, nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    coordinates = db.Column(JSON, nullable=True)
    picturePath = db.Column(db.String(255), nullable=True)
    favorite = db.Column(db.Boolean, nullable=True)
    horseId = db.Column(db.Integer, db.ForeignKey('Horses.idHorse'), nullable=False)
    veterinarianId = db.Column(db.Integer, db.ForeignKey('Veterinarians.idVeterinarian'), nullable=True)
    appointmentId = db.Column(db.Integer, db.ForeignKey('Appointments.idAppointment'), nullable=True)
