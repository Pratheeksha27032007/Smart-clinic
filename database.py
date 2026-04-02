from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80),  nullable=False, unique=True)
    email        = db.Column(db.String(120), nullable=False, unique=True)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(30),  nullable=False)  # doctor / pharmacy / hospital
    full_name    = db.Column(db.String(120))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password, pwd)

class Medicine(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    category      = db.Column(db.String(50))
    quantity      = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=20)
    unit_price    = db.Column(db.Float, default=0.0)
    last_updated  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Doctor(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    specialty      = db.Column(db.String(100))
    available_days = db.Column(db.String(100))
    appointments   = db.relationship('Appointment', backref='doctor', lazy=True)

class Appointment(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    patient_name     = db.Column(db.String(100), nullable=False)
    patient_age      = db.Column(db.Integer)
    symptoms         = db.Column(db.Text)
    doctor_id        = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)