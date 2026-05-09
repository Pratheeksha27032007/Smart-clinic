from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re

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

class PatientProfile(db.Model):
    """Store comprehensive patient health information"""
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    allergies         = db.Column(db.Text)  # Comma-separated or JSON
    chronic_conditions = db.Column(db.Text)  # Ongoing medical conditions
    emergency_contact = db.Column(db.String(120))
    emergency_phone   = db.Column(db.String(20))
    medical_notes     = db.Column(db.Text)  # Doctor's notes
    last_checkup      = db.Column(db.DateTime)
    insurance_provider = db.Column(db.String(100))
    insurance_id      = db.Column(db.String(50))
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='patient_profile')

class Medicine(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    category      = db.Column(db.String(50))
    quantity      = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=20)
    unit_price    = db.Column(db.Float, default=0.0)
    contraindications = db.Column(db.Text)  # Warnings, allergies
    side_effects  = db.Column(db.Text)
    last_updated  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Doctor(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    specialty      = db.Column(db.String(100))
    available_days = db.Column(db.String(100))
    start_time     = db.Column(db.String(10), default="09:00")  # HH:MM
    end_time       = db.Column(db.String(10), default="17:00")
    consultation_fee = db.Column(db.Float, default=500.0)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    appointments   = db.relationship('Appointment', backref='doctor', lazy=True)
    prescriptions  = db.relationship('Prescription', backref='doctor', lazy=True)

class Appointment(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    patient_name     = db.Column(db.String(100), nullable=False)
    patient_age      = db.Column(db.Integer)
    symptoms         = db.Column(db.Text)
    doctor_id        = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    status           = db.Column(db.String(20), default='pending')  # pending/accepted/declined/completed/cancelled
    notes            = db.Column(db.Text)
    patient_user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at     = db.Column(db.DateTime)
    
    patient = db.relationship('User', foreign_keys=[patient_user_id])
    prescriptions = db.relationship('Prescription', backref='appointment', lazy=True)

class Prescription(db.Model):
    """Doctor prescriptions to patients"""
    id              = db.Column(db.Integer, primary_key=True)
    doctor_id       = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id  = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    medicines       = db.Column(db.JSON)  # [{"medicine_id": 1, "dosage": "500mg", "frequency": "2x daily", "days": 7}]
    instructions    = db.Column(db.Text)  # Special instructions
    status          = db.Column(db.String(20), default='pending')  # pending/dispensed/completed
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at      = db.Column(db.DateTime)  # Prescriptions expire after 30 days
    
    patient = db.relationship('User', foreign_keys=[patient_id], backref='prescriptions')

class Order(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    patient_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=True)
    medicine_id    = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity       = db.Column(db.Integer, default=1)
    total_price    = db.Column(db.Float, default=0.0)
    status         = db.Column(db.String(30), default='pending')  # pending/accepted/packing/shipped/delivered
    address        = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='pending')  # pending/paid/failed
    payment_method = db.Column(db.String(30))  # cash/card/upi
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at   = db.Column(db.DateTime)
    
    patient        = db.relationship('User', foreign_keys=[patient_id])
    medicine       = db.relationship('Medicine')
    prescription   = db.relationship('Prescription', backref='orders')

class Message(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender      = db.relationship('User', foreign_keys=[sender_id])
    receiver    = db.relationship('User', foreign_keys=[receiver_id])

class ActivityLog(db.Model):
    """Audit trail for all important actions"""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action      = db.Column(db.String(100), nullable=False)
    details     = db.Column(db.Text)
    ip_address  = db.Column(db.String(45))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)