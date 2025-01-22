from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Client(db.Model):
    __tablename__ = 'Clients'
    
    idClient = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(20), nullable=True)
    phoneCountryCode = db.Column(db.String(10), nullable=True)

    def __init__(self, name, email=None, phoneNumber=None, phoneCountryCode=None):
        self.name = name
        self.email = email
        self.phoneNumber = phoneNumber
        self.phoneCountryCode = phoneCountryCode


class Horse(db.Model):
    __tablename__ = 'Horses'
    
    idHorse = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    profilePicturePath = db.Column(db.String(255), nullable=True)
    birthDate = db.Column(db.Date, nullable=True)
    pictureRightFrontPath = db.Column(db.String(255), nullable=True)
    pictureLeftFrontPath = db.Column(db.String(255), nullable=True)
    pictureRightHindPath = db.Column(db.String(255), nullable=True)
    pictureLeftHindPath = db.Column(db.String(255), nullable=True)

    def __init__(self, name, profilePicturePath=None, birthDate=None, pictureRightFrontPath=None, pictureLeftFrontPath=None, pictureRightHindPath=None, pictureLeftHindPath=None):
        self.name = name
        self.profilePicturePath = profilePicturePath
        self.birthDate = birthDate
        self.pictureRightFrontPath = pictureRightFrontPath
        self.pictureLeftFrontPath = pictureLeftFrontPath
        self.pictureRightHindPath = pictureRightHindPath
        self.pictureLeftHindPath = pictureLeftHindPath