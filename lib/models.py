from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Horse(db.Model):
    __tablename__ = 'Horses'

    id = db.Column('idHorse', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(255), nullable=False)
    profile_picture_path = db.Column('profilePicturePath', db.String(255), nullable=True)
    birth_date = db.Column('birthDate', db.DateTime, nullable=True)
    picture_right_front_path = db.Column('pictureRightFrontPath', db.String(255), nullable=True)
    picture_left_front_path = db.Column('pictureLeftFrontPath', db.String(255), nullable=True)
    picture_right_hind_path = db.Column('pictureRightHindPath', db.String(255), nullable=True)
    picture_left_hind_path = db.Column('pictureLeftHindPath', db.String(255), nullable=True)

    clients = db.relationship('ClientsHasHorses', back_populates='horse', cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', back_populates='horse', cascade="all, delete-orphan")


class Client(db.Model):
    __tablename__ = 'Clients'

    id = db.Column('idClient', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(255), nullable=False)
    email = db.Column('email', db.String(255), nullable=True)
    phone_number = db.Column('phoneNumber', db.String(20), nullable=True)
    phone_country_code = db.Column('phoneCountryCode', db.String(10), nullable=True)

    horses = db.relationship('ClientsHasHorses', back_populates='client', cascade="all, delete-orphan")


class ClientsHasHorses(db.Model):
    __tablename__ = 'Clients_has_horses'

    client_id = db.Column('Clients_idClient', db.Integer, db.ForeignKey('Clients.idClient'), primary_key=True)
    horse_id = db.Column('horses_idHorse', db.Integer, db.ForeignKey('Horses.idHorse'), primary_key=True)
    is_client_horse_owner = db.Column('isClientHorseOwner', db.Boolean, nullable=False)

    client = db.relationship('Client', back_populates='horses')
    horse = db.relationship('Horse', back_populates='clients')


class Veterinarian(db.Model):
    __tablename__ = 'Veterinarians'

    id = db.Column('idVeterinary', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(255), nullable=False)
    email = db.Column('email', db.String(255), nullable=True)
    phone_number = db.Column('phoneNumber', db.String(20), nullable=True)
    phone_country_code = db.Column('phoneCountryCode', db.String(10), nullable=True)
    password = db.Column('password', db.String(255), nullable=True)
    id_cedula_profissional = db.Column('idCedulaProfissional', db.String(40), nullable=False)

    appointments = db.relationship('Appointment', back_populates='veterinarian', cascade="all, delete-orphan")


class Appointment(db.Model):
    __tablename__ = 'Appointments'

    id = db.Column('idAppointment', db.Integer, primary_key=True, autoincrement=True)
    horse_id = db.Column('horseId', db.Integer, db.ForeignKey('Horses.idHorse'), nullable=False)
    veterinary_id = db.Column('veterinaryID', db.Integer, db.ForeignKey('Veterinarians.idVeterinary'), nullable=False)
    lameness_right_front = db.Column('lamenessRightFront', db.Integer, nullable=True)
    lameness_left_front = db.Column('lamenessLeftFront', db.Integer, nullable=True)
    lameness_right_hind = db.Column('lamenessRighHind', db.Integer, nullable=True)
    lameness_left_hind = db.Column('lamenessLeftHind', db.Integer, nullable=True)

    horse = db.relationship('Horse', back_populates='appointments')
    veterinarian = db.relationship('Veterinarian', back_populates='appointments')
    measures = db.relationship('Measure', back_populates='appointment', cascade="all, delete-orphan")
    cbcs = db.relationship('CBC', back_populates='appointment', cascade="all, delete-orphan")


class Measure(db.Model):
    __tablename__ = 'Measures'

    id = db.Column('idMeasure', db.Integer, primary_key=True, autoincrement=True)
    vet_appointment = db.Column('vetAppointment', db.Integer, db.ForeignKey('Appointments.idAppointment'), nullable=False)
    user_bw = db.Column('userBW', db.Integer, nullable=True)
    algorithm_bw = db.Column('algorithmBW', db.Integer, nullable=True)
    user_bcs = db.Column('userBCS', db.Integer, nullable=True)
    algorithm_bcs = db.Column('algorithmBCS', db.Integer, nullable=True)
    bpm = db.Column('BPM', db.Integer, nullable=True)
    ecg_time = db.Column('ECGtime', db.String(10), nullable=True)
    muscle_tension_frequency = db.Column('muscleTensionFrequency', db.String(255), nullable=True)
    muscle_tension_stiffness = db.Column('muscleTensionStifness', db.String(255), nullable=True)
    muscle_tension_r = db.Column('muscleTensionR', db.String(255), nullable=True)

    appointment = db.relationship('Appointment', back_populates='measures')
    pictures = db.relationship('Picture', back_populates='measure', cascade="all, delete-orphan")


class Picture(db.Model):
    __tablename__ = 'Pictures'

    id = db.Column('idPicture', db.Integer, primary_key=True, autoincrement=True)
    measure_id = db.Column('measureID', db.Integer, db.ForeignKey('Measures.idMeasure'), nullable=False)
    path = db.Column('path', db.String(255), nullable=False)
    date = db.Column('date', db.DateTime, nullable=False, default=datetime.utcnow)

    measure = db.relationship('Measure', back_populates='pictures')


class CBC(db.Model):
    __tablename__ = 'CBC'

    id = db.Column('idCBC', db.Integer, primary_key=True, autoincrement=True)
    vet_appointment = db.Column('vetAppointment', db.Integer, db.ForeignKey('Appointments.idAppointment'), nullable=False)
    path = db.Column('path', db.String(255), nullable=False)
    date = db.Column('date', db.DateTime, nullable=False, default=datetime.utcnow)
    
    appointment = db.relationship('Appointment', back_populates='cbcs')