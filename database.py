from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80),  nullable=False, unique=True)
    email        = db.Column(db.String(120), nullable=False, unique=True)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(30),  nullable=False)
    full_name    = db.Column(db.String(120))
    phone        = db.Column(db.String(20))
    age          = db.Column(db.Integer)
    blood_group  = db.Column(db.String(5))
    specialization = db.Column(db.String(100))
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
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    appointments   = db.relationship('Appointment', backref='doctor', lazy=True)

class Appointment(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    patient_name     = db.Column(db.String(100), nullable=False)
    patient_age      = db.Column(db.Integer)
    symptoms         = db.Column(db.Text)
    doctor_id        = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    status           = db.Column(db.String(20), default='pending')  # pending/accepted/declined
    patient_user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    patient_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medicine_id    = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity       = db.Column(db.Integer, default=1)
    total_price    = db.Column(db.Float, default=0.0)
    status         = db.Column(db.String(30), default='pending')  # pending/accepted/packing/shipped/delivered
    address        = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    patient        = db.relationship('User', foreign_keys=[patient_id])
    medicine       = db.relationship('Medicine')

class Message(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    sender      = db.relationship('User', foreign_keys=[sender_id])
    receiver    = db.relationship('User', foreign_keys=[receiver_id])