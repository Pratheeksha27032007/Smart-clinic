from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import db, User, Medicine, Appointment, Doctor, Order, Message, PatientProfile, Prescription, ActivityLog
from datetime import datetime, date, timedelta
from groq import Groq
from functools import wraps
import json, os, re, logging
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartclinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'smartclinic-secret-2024')
db.init_app(app)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── VALIDATION HELPERS ──────────────────────────────────
def validate_password(pwd):
    """Ensure strong password"""
    if len(pwd) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', pwd):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[0-9]', pwd):
        return False, "Password must contain number"
    if not re.search(r'[!@#$%^&*]', pwd):
        return False, "Password must contain special character (!@#$%^&*)"
    return True, ""

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone format"""
    phone = re.sub(r'\D', '', phone)
    return len(phone) >= 10

def validate_appointment_date(date_str):
    """Ensure appointment is in future"""
    try:
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if appt_date < date.today():
            return False, "Appointment date must be in the future"
        if appt_date > date.today() + timedelta(days=90):
            return False, "Cannot book more than 90 days in advance"
        return True, ""
    except:
        return False, "Invalid date format"

def log_activity(user_id, action, details=None, ip=None):
    """Log user actions for audit trail"""
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip or request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_role(roles):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            role = session.get('role')
            if not role or role not in (roles if isinstance(roles, (list, tuple)) else [roles]):
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ── AI FUNCTIONS ────────────────────────────────────────
def ai(prompt):
    """Call Groq API for AI responses"""
    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role":"system","content":"You are a helpful SmartClinic assistant. Be concise and accurate."},
                {"role":"user","content":prompt}
            ],
            max_tokens=500
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "AI service temporarily unavailable."

def time_of_day():
    h = datetime.now().hour
    return "morning" if h < 12 else "afternoon" if h < 17 else "evening"

# ── DATABASE SEEDING ────────────────────────────────────
def seed_data():
    """Seed initial data with validation"""
    presets = [
        {"email":"doctor@smartclinic.com","username":"doctor1","role":"doctor","full_name":"Dr. Priya Sharma","specialization":"General Physician","password":"Doctor@123"},
        {"email":"pharmacy@smartclinic.com","username":"pharmacy1","role":"pharmacy","full_name":"Pharmacy Staff","specialization":"Pharmacy","password":"Pharma@123"},
        {"email":"admin@smartclinic.com","username":"admin1","role":"hospital","full_name":"Hospital Admin","specialization":"Management","password":"Admin@123"},
    ]
    
    for p in presets:
        if not User.query.filter_by(email=p['email']).first():
            u = User(
                username=p['username'],
                email=p['email'],
                role=p['role'],
                full_name=p['full_name'],
                specialization=p['specialization']
            )
            u.set_password(p['password'])
            db.session.add(u)

    if Doctor.query.count() == 0:
        doc_user = User.query.filter_by(email='doctor@smartclinic.com').first()
        doctors = [
            Doctor(name="Dr. Riya Sharma", specialty="General Physician", available_days="Mon,Tue,Wed,Thu,Fri", user_id=doc_user.id if doc_user else None, consultation_fee=500),
            Doctor(name="Dr. Arjun Mehta", specialty="Cardiologist", available_days="Mon,Wed,Fri", consultation_fee=800),
            Doctor(name="Dr. Sneha Patel", specialty="Dermatologist", available_days="Tue,Thu,Sat", consultation_fee=600),
            Doctor(name="Dr. Rahul Verma", specialty="Orthopedic", available_days="Mon,Tue,Thu,Fri", consultation_fee=700),
        ]
        db.session.add_all(doctors)

    if Medicine.query.count() == 0:
        medicines = [
            Medicine(name="Paracetamol 500mg", category="Analgesic", quantity=120, reorder_level=30, unit_price=2.5),
            Medicine(name="Amoxicillin 250mg", category="Antibiotic", quantity=18, reorder_level=25, unit_price=8.0),
            Medicine(name="Cetirizine 10mg", category="Antihistamine", quantity=60, reorder_level=20, unit_price=3.0),
            Medicine(name="Metformin 500mg", category="Antidiabetic", quantity=200, reorder_level=50, unit_price=4.5),
            Medicine(name="Omeprazole 20mg", category="Antacid", quantity=12, reorder_level=20, unit_price=6.0),
            Medicine(name="Ibuprofen 400mg", category="NSAID", quantity=75, reorder_level=30, unit_price=3.5),
            Medicine(name="Azithromycin 500mg", category="Antibiotic", quantity=8, reorder_level=15, unit_price=12.0),
        ]
        db.session.add_all(medicines)
    
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_data()

# ── AUTH ROUTES ─────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        pwd = request.form.get('password','')
        role = request.form.get('role','patient')
        
        if not email or not pwd:
            return render_template('login.html', error='Email and password required.')
        
        user = User.query.filter_by(email=email, role=role).first()
        if user and user.check_password(pwd):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['full_name'] = user.full_name or user.username
            session['blood_group'] = user.blood_group
            session['age'] = user.age
            
            log_activity(user.id, f"LOGIN_{role.upper()}")
            return redirect(url_for('index'))
        
        log_activity(None, "FAILED_LOGIN", f"email={email}, role={role}")
        return render_template('login.html', error='Invalid credentials or wrong role selected.')
    
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        username = request.form.get('username','').strip()
        pwd = request.form.get('password','')
        full_name = request.form.get('full_name','').strip()
        phone = request.form.get('phone','').strip()
        age = request.form.get('age','')
        blood_group = request.form.get('blood_group','')
        
        # Validations
        if not all([email, username, pwd, full_name]):
            return render_template('register.html', error='All fields required.')
        
        if not validate_email(email):
            return render_template('register.html', error='Invalid email format.')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered.')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already taken.')
        
        valid, msg = validate_password(pwd)
        if not valid:
            return render_template('register.html', error=msg)
        
        if phone and not validate_phone(phone):
            return render_template('register.html', error='Invalid phone number.')
        
        try:
            u = User(username=username, email=email, role='patient', full_name=full_name,
                    phone=phone, age=int(age) if age else None, blood_group=blood_group or None)
            u.set_password(pwd)
            db.session.add(u)
            db.session.flush()
            
            profile = PatientProfile(user_id=u.id)
            db.session.add(profile)
            db.session.commit()
            
            log_activity(u.id, "REGISTER")
            return render_template('register.html', success='Account created! Please log in.')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return render_template('register.html', error='Registration failed. Please try again.')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, "LOGOUT")
    session.clear()
    return redirect(url_for('login'))

# ── MAIN DASHBOARD ──────────────────────────────────────
@app.route('/')
def index():
    role = session.get('role', 'guest')
    today = date.today()
    
    if role == 'doctor':
        user_id = session.get('user_id')
        doctor = Doctor.query.filter_by(user_id=user_id).first()
        
        today_appts = Appointment.query.filter(
            Appointment.doctor_id == doctor.id if doctor else None,
            Appointment.appointment_date == str(today)
        ).all() if doctor else []
        
        pending_appts = len([a for a in today_appts if a.status == 'pending'])
        accepted_appts = len([a for a in today_appts if a.status == 'accepted'])
        
        unread_msgs = Message.query.filter_by(receiver_id=user_id, is_read=False).count()
        
        return render_template('index.html', 
            role='doctor',
            time_of_day=time_of_day(),
            today_appts=len(today_appts),
            pending_appts=pending_appts,
            accepted_appts=accepted_appts,
            unread_msgs=unread_msgs,
            todays_list=today_appts,
            recent_msgs=Message.query.filter(
                (Message.sender_id==user_id)|(Message.receiver_id==user_id)
            ).order_by(Message.created_at.desc()).limit(5).all()
        )
    
    elif role == 'pharmacy':
        total_meds = Medicine.query.count()
        low_stock = len(Medicine.query.filter(Medicine.quantity <= Medicine.reorder_level).all())
        pending_orders = Order.query.filter_by(status='pending').count()
        delivered_today = Order.query.filter(
            Order.status=='delivered',
            Order.delivered_at >= datetime.combine(today, datetime.min.time())
        ).count()
        
        return render_template('index.html',
            role='pharmacy',
            total_meds=total_meds,
            low_stock=low_stock,
            pending_orders=pending_orders,
            delivered_today=delivered_today,
            orders_list=Order.query.filter_by(status='pending').limit(5).all(),
            low_stock_list=Medicine.query.filter(Medicine.quantity <= Medicine.reorder_level).limit(5).all()
        )
    
    elif role == 'hospital':
        total_doctors = Doctor.query.count()
        total_patients = User.query.filter_by(role='patient').count()
        total_orders = Order.query.count()
        shipping_orders = Order.query.filter(Order.status.in_(['packing', 'shipped'])).count()
        
        return render_template('index.html',
            role='hospital',
            total_doctors=total_doctors,
            total_patients=total_patients,
            total_orders=total_orders,
            shipping_orders=shipping_orders,
            doctors_list=Doctor.query.limit(10).all(),
            recent_shipments=Order.query.order_by(Order.created_at.desc()).limit(5).all()
        )
    
    elif role == 'patient':
        user_id = session.get('user_id')
        my_appts = Appointment.query.filter_by(patient_user_id=user_id).count()
        my_orders = Order.query.filter_by(patient_id=user_id).count()
        accepted = Appointment.query.filter_by(patient_user_id=user_id, status='accepted').count()
        in_transit = Order.query.filter(
            Order.patient_id==user_id,
            Order.status.in_(['packing','shipped'])
        ).count()
        
        return render_template('index.html',
            role='patient',
            my_appts=my_appts,
            my_orders=my_orders,
            accepted=accepted,
            in_transit=in_transit
        )
    
    else:
        # Guest/not logged in
        return render_template('index.html',
            role='guest',
            total_medicines=Medicine.query.count(),
            total_doctors=Doctor.query.count(),
            today_appointments=Appointment.query.filter(Appointment.appointment_date==str(today)).count(),
            low_stock=len(Medicine.query.filter(Medicine.quantity <= Medicine.reorder_level).all())
        )

# ── PATIENT ROUTES ──────────────────────────────────────
@app.route('/patient/appointments')
@require_login
@require_role('patient')
def patient_appointments():
    user_id = session.get('user_id')
    today = date.today().isoformat()
    doctors = Doctor.query.all()
    appointments = Appointment.query.filter_by(patient_user_id=user_id).all()
    
    return render_template('patient_appointments.html',
        doctors=doctors,
        appointments=appointments,
        today=today,
        success=request.args.get('success'),
        error=request.args.get('error')
    )

@app.route('/patient/book', methods=['POST'])
@require_login
@require_role('patient')
def patient_book():
    user_id = session.get('user_id')
    doctor_id = request.form.get('doctor_id')
    appt_date = request.form.get('appointment_date')
    appt_time = request.form.get('appointment_time')
    symptoms = request.form.get('symptoms','').strip()
    
    if not doctor_id or not appt_date or not appt_time:
        return redirect(url_for('patient_appointments', error='Please select a doctor, date and time.'))

    try:
        doctor_id = int(doctor_id)
    except ValueError:
        return redirect(url_for('patient_appointments', error='Selected doctor is invalid.'))

    valid, msg = validate_appointment_date(appt_date)
    if not valid:
        return redirect(url_for('patient_appointments', error=msg))

    existing_doctor_conflict = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=appt_date,
        appointment_time=appt_time
    ).filter(Appointment.status.in_(['pending','accepted'])).first()

    if existing_doctor_conflict:
        return redirect(url_for('patient_appointments', error='That doctor already has an appointment at the selected time.'))

    existing_patient_conflict = Appointment.query.filter_by(
        patient_user_id=user_id,
        appointment_date=appt_date,
        appointment_time=appt_time
    ).filter(Appointment.status.in_(['pending','accepted'])).first()

    if existing_patient_conflict:
        return redirect(url_for('patient_appointments', error='You already have another appointment at that time.'))
    
    try:
        appt = Appointment(
            patient_name=session.get('full_name',''),
            patient_age=session.get('age'),
            symptoms=symptoms,
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            patient_user_id=user_id
        )
        db.session.add(appt)
        db.session.commit()
        log_activity(user_id, "BOOK_APPOINTMENT", f"doctor_id={doctor_id}")
        return redirect(url_for('patient_appointments', success='Appointment booked successfully.'))
    except Exception as e:
        logger.error(f"Booking error: {e}")
        return redirect(url_for('patient_appointments', error='Booking failed'))

@app.route('/patient/cancel/<int:id>', methods=['POST'])
@require_login
@require_role('patient')
def patient_cancel(id):
    appt = Appointment.query.get_or_404(id)
    if appt.patient_user_id != session.get('user_id'):
        return redirect(url_for('patient_appointments'))
    appt.status = 'cancelled'
    db.session.commit()
    return redirect(url_for('patient_appointments'))

@app.route('/patient/profile')
@require_login
@require_role('patient')
def patient_profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    profile = PatientProfile.query.filter_by(user_id=user_id).first()
    prescriptions = Prescription.query.filter_by(patient_id=user_id).order_by(Prescription.created_at.desc()).all()
    
    return render_template('patient_Profile.html',
        user=user,
        profile=profile,
        prescriptions=prescriptions,
        success=request.args.get('success'),
        error=request.args.get('error')
    )

@app.route('/patient/profile', methods=['POST'])
@require_login
@require_role('patient')
def patient_profile_update():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    full_name = request.form.get('full_name','').strip()
    phone = request.form.get('phone','').strip()
    age = request.form.get('age','').strip()
    blood_group = request.form.get('blood_group','').strip()

    if phone and not validate_phone(phone):
        return redirect(url_for('patient_profile', error='Invalid phone number'))
    if age and not age.isdigit():
        return redirect(url_for('patient_profile', error='Age must be a number'))

    user.full_name = full_name or user.full_name
    user.phone = phone or user.phone
    user.age = int(age) if age else user.age
    user.blood_group = blood_group or user.blood_group

    profile = PatientProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = PatientProfile(user_id=user_id)
        db.session.add(profile)
    
    profile.allergies = request.form.get('allergies','').strip()
    profile.chronic_conditions = request.form.get('chronic_conditions','').strip()
    profile.emergency_contact = request.form.get('emergency_contact','').strip()
    profile.emergency_phone = request.form.get('emergency_phone','').strip()
    profile.insurance_provider = request.form.get('insurance_provider','').strip()
    profile.insurance_id = request.form.get('insurance_id','').strip()
    
    db.session.commit()
    session['full_name'] = user.full_name
    session['phone'] = user.phone
    session['age'] = user.age
    session['blood_group'] = user.blood_group
    log_activity(user_id, "UPDATE_PROFILE")
    return redirect(url_for('patient_profile', success='Profile saved successfully.'))

@app.route('/patient/medicines')
@require_login
@require_role('patient')
def patient_medicines():
    medicines = Medicine.query.all()
    return render_template('patient_medicines.html',
        medicines=medicines,
        success=request.args.get('success'),
        error=request.args.get('error')
    )

@app.route('/patient/order', methods=['POST'])
@require_login
@require_role('patient')
def patient_order():
    user_id = session.get('user_id')
    med_id = int(request.form.get('medicine_id'))
    qty = int(request.form.get('quantity', 1))
    address = request.form.get('address','').strip()
    
    medicine = Medicine.query.get(med_id)
    if not medicine or qty > medicine.quantity:
        return redirect(url_for('patient_medicines', error='Invalid order'))
    
    try:
        order = Order(
            patient_id=user_id,
            medicine_id=med_id,
            quantity=qty,
            total_price=medicine.unit_price * qty,
            address=address
        )
        medicine.quantity -= qty
        db.session.add(order)
        db.session.commit()
        log_activity(user_id, "PLACE_ORDER", f"medicine_id={med_id}, qty={qty}")
        return redirect(url_for('patient_orders', success='Order placed successfully'))
    except Exception as e:
        logger.error(f"Order error: {e}")
        db.session.rollback()
        return redirect(url_for('patient_medicines', error='Order failed'))

@app.route('/patient/orders')
@require_login
@require_role('patient')
def patient_orders():
    user_id = session.get('user_id')
    orders = Order.query.filter_by(patient_id=user_id).order_by(Order.created_at.desc()).all()
    return render_template('patient_orders.html',
        orders=orders,
        success=request.args.get('success'),
        error=request.args.get('error')
    )

# ── DOCTOR ROUTES ───────────────────────────────────────
@app.route('/doctor/appointments')
@require_login
@require_role('doctor')
def doctor_appointments():
    user_id = session.get('user_id')
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    
    filter_by = request.args.get('filter', 'all')
    query = Appointment.query.filter_by(doctor_id=doctor.id) if doctor else Appointment.query
    
    if filter_by == 'pending':
        query = query.filter_by(status='pending')
    elif filter_by == 'accepted':
        query = query.filter_by(status='accepted')
    elif filter_by == 'today':
        query = query.filter_by(appointment_date=str(date.today()))
    
    appointments = query.order_by(Appointment.created_at.desc()).all()
    pending_count = Appointment.query.filter_by(doctor_id=doctor.id, status='pending').count() if doctor else 0
    patient_history = {}
    if doctor:
        patient_ids = {a.patient_user_id for a in appointments if a.patient_user_id}
        for pid in patient_ids:
            last_appt = Appointment.query.filter_by(doctor_id=doctor.id, patient_user_id=pid).order_by(Appointment.created_at.desc()).first()
            rx_count = Prescription.query.filter_by(doctor_id=doctor.id, patient_id=pid).count()
            patient_history[pid] = {
                'last_appointment': {
                    'date': last_appt.appointment_date if last_appt else None,
                    'time': last_appt.appointment_time if last_appt else None,
                    'status': last_appt.status if last_appt else None,
                    'symptoms': last_appt.symptoms if last_appt else None
                },
                'prescription_count': rx_count
            }
    
    return render_template('doctor_appointments.html',
        appointments=appointments,
        filter=filter_by,
        pending_count=pending_count,
        doctor=doctor,
        patient_history=patient_history,
        success=request.args.get('success'),
        error=request.args.get('error')
    )

@app.route('/doctor/accept/<int:id>', methods=['POST'])
@require_login
@require_role('doctor')
def doctor_accept(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = 'accepted'
    db.session.commit()
    return redirect(url_for('doctor_appointments', success='Appointment accepted.'))

@app.route('/doctor/decline/<int:id>', methods=['POST'])
@require_login
@require_role('doctor')
def doctor_decline(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = 'declined'
    db.session.commit()
    return redirect(url_for('doctor_appointments', success='Appointment declined.'))

@app.route('/doctor/set-schedule', methods=['POST'])
@require_login
@require_role('doctor')
def doctor_set_schedule():
    user_id = session.get('user_id')
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if doctor:
        doctor.available_days = request.form.get('available_days','')
        doctor.start_time = request.form.get('start_time','09:00')
        doctor.end_time = request.form.get('end_time','17:00')
        db.session.commit()
    return redirect(url_for('doctor_appointments', success='Schedule updated.'))

@app.route('/doctor/prescriptions')
@require_login
@require_role('doctor')
def doctor_prescriptions():
    user_id = session.get('user_id')
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    medicines = Medicine.query.all()
    medicines_map = {m.id: m.name for m in medicines}
    patients = User.query.filter_by(role='patient').all()
    prescriptions = Prescription.query.filter_by(doctor_id=doctor.id).order_by(Prescription.created_at.desc()).all() if doctor else []
    patient_history = {}
    if doctor:
        for p in patients:
            recent_appts = Appointment.query.filter_by(doctor_id=doctor.id, patient_user_id=p.id).order_by(Appointment.created_at.desc()).limit(3).all()
            recent_rxs = Prescription.query.filter_by(doctor_id=doctor.id, patient_id=p.id).order_by(Prescription.created_at.desc()).limit(3).all()
            patient_history[p.id] = {
                'last_appointment': {
                    'date': recent_appts[0].appointment_date if recent_appts else None,
                    'time': recent_appts[0].appointment_time if recent_appts else None,
                    'status': recent_appts[0].status if recent_appts else None,
                    'symptoms': recent_appts[0].symptoms if recent_appts else None
                },
                'recent_appointments': [
                    {
                        'date': appt.appointment_date,
                        'time': appt.appointment_time,
                        'status': appt.status,
                        'symptoms': appt.symptoms
                    } for appt in recent_appts
                ],
                'prescription_count': Prescription.query.filter_by(doctor_id=doctor.id, patient_id=p.id).count(),
                'recent_prescriptions': [
                    {
                        'created_at': rx.created_at.strftime('%d %b %Y'),
                        'status': rx.status,
                        'medicines': [med.get('medicine_name') or med.get('medicine_id') for med in rx.medicines]
                    } for rx in recent_rxs
                ]
            }
    
    return render_template('doctor_prescription.html',
        medicines=medicines,
        medicines_map=medicines_map,
        patients=patients,
        prescriptions=prescriptions,
        doctor=doctor,
        patient_history=patient_history
    )

@app.route('/doctor/prescriptions', methods=['POST'])
@require_login
@require_role('doctor')
def doctor_create_prescription():
    user_id = session.get('user_id')
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    
    if not doctor:
        return jsonify({'error':'Unable to identify doctor.'}), 400
    
    try:
        patient_id = int(request.form.get('patient_id'))
        medicines = json.loads(request.form.get('medicines','[]'))
        instructions = request.form.get('instructions','').strip()
        
        if not medicines:
            return jsonify({'error':'Please add at least one medicine.'}), 400
        
        prescription = Prescription(
            doctor_id=doctor.id,
            patient_id=patient_id,
            medicines=medicines,
            instructions=instructions,
            expires_at=datetime.now() + timedelta(days=30)
        )
        db.session.add(prescription)
        db.session.commit()
        log_activity(user_id, "CREATE_PRESCRIPTION", f"patient_id={patient_id}")
        return jsonify({'success':True})
    except Exception as e:
        logger.error(f"Prescription error: {e}")
        return jsonify({'error':'Prescription creation failed.'}), 500

@app.route('/doctor/prescriptions/dispense/<int:id>', methods=['POST'])
@require_login
@require_role('doctor')
def doctor_dispense_prescription(id):
    prescription = Prescription.query.get_or_404(id)
    doctor = Doctor.query.filter_by(user_id=session.get('user_id')).first()
    if not doctor or prescription.doctor_id != doctor.id:
        return jsonify({'error':'Unauthorized'}), 403
    prescription.status = 'dispensed'
    db.session.commit()
    return jsonify({'success':True})

@app.route('/doctor/prescriptions/print/<int:id>')
@require_login
@require_role('doctor')
def doctor_print_prescription(id):
    prescription = Prescription.query.get_or_404(id)
    doctor = Doctor.query.filter_by(user_id=session.get('user_id')).first()
    if not doctor or prescription.doctor_id != doctor.id:
        return redirect(url_for('doctor_prescriptions'))

    patient = User.query.get(prescription.patient_id)
    return render_template('doctor_prescription_print.html',
        prescription=prescription,
        patient=patient,
        doctor=doctor
    )

# ── PHARMACY ROUTES ─────────────────────────────────────
@app.route('/pharmacy/stock')
@require_login
@require_role('pharmacy')
def pharmacy_stock():
    medicines = Medicine.query.all()
    low_stock = [m for m in medicines if m.quantity <= m.reorder_level]
    
    return render_template('pharmacy_stock.html',
        medicines=medicines,
        low_stock=low_stock
    )

@app.route('/pharmacy/stock/add', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_add_medicine():
    try:
        medicine = Medicine(
            name=request.form.get('name'),
            category=request.form.get('category'),
            quantity=int(request.form.get('quantity',0)),
            reorder_level=int(request.form.get('reorder_level',20)),
            unit_price=float(request.form.get('unit_price',0))
        )
        db.session.add(medicine)
        db.session.commit()
        log_activity(session.get('user_id'), "ADD_MEDICINE")
        return redirect(url_for('pharmacy_stock'))
    except Exception as e:
        logger.error(f"Add medicine error: {e}")
        return redirect(url_for('pharmacy_stock'))

@app.route('/pharmacy/stock/update/<int:id>', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_update_medicine(id):
    medicine = Medicine.query.get_or_404(id)
    medicine.quantity = int(request.form.get('quantity', 0))
    db.session.commit()
    return redirect(url_for('pharmacy_stock'))

@app.route('/pharmacy/stock/delete/<int:id>', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_delete_medicine(id):
    medicine = Medicine.query.get_or_404(id)
    db.session.delete(medicine)
    db.session.commit()
    return redirect(url_for('pharmacy_stock'))

@app.route('/pharmacy/orders')
@require_login
@require_role('pharmacy')
def pharmacy_orders():
    filter_by = request.args.get('filter', 'all')
    query = Order.query.join(Medicine).join(User, Order.patient_id == User.id)
    
    if filter_by != 'all':
        query = query.filter(Order.status == filter_by)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('pharmacy_orders.html',
        orders=orders,
        filter=filter_by
    )

@app.route('/pharmacy/accept-order/<int:id>', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_accept_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'accepted'
    db.session.commit()
    return redirect(url_for('pharmacy_orders'))

@app.route('/pharmacy/pack-order/<int:id>', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_pack_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'packing'
    db.session.commit()
    return redirect(url_for('pharmacy_orders'))

@app.route('/pharmacy/ship-order/<int:id>', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_ship_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'shipped'
    db.session.commit()
    return redirect(url_for('pharmacy_orders'))

@app.route('/pharmacy/deliver/<int:id>', methods=['POST'])
@require_login
@require_role('pharmacy')
def pharmacy_deliver(id):
    order = Order.query.get_or_404(id)
    if order.status == 'shipped':
        order.status = 'delivered'
        order.delivered_at = datetime.now()
        db.session.commit()
    return redirect(url_for('pharmacy_orders'))

# ── PUBLIC/GUEST ROUTES ─────────────────────────────────
@app.route('/appointments', methods=['GET','POST'])
def appointments():
    """Guest appointment booking"""
    doctors = Doctor.query.all()
    today = date.today().isoformat()
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    
    if request.method == 'POST':
        try:
            appt = Appointment(
                patient_name=request.form.get('patient_name'),
                patient_age=int(request.form.get('patient_age',0)),
                symptoms=request.form.get('symptoms','').strip(),
                doctor_id=int(request.form.get('doctor_id')),
                appointment_date=request.form.get('appointment_date'),
                appointment_time=request.form.get('appointment_time')
            )
            db.session.add(appt)
            db.session.commit()
            log_activity(None, "GUEST_APPOINTMENT")
            return render_template('appointments.html', doctors=doctors, appointments=appointments, success='Appointment booked!')
        except Exception as e:
            logger.error(f"Guest appointment error: {e}")
            return render_template('appointments.html', doctors=doctors, appointments=appointments, error='Booking failed')
    
    return render_template('appointments.html', doctors=doctors, appointments=appointments, today=today)

@app.route('/appointments/delete/<int:id>', methods=['POST'])
def appointments_delete(id):
    appt = Appointment.query.get_or_404(id)
    if appt.patient_user_id and appt.patient_user_id != session.get('user_id'):
        return redirect(url_for('appointments'))
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for('appointments'))

@app.route('/stock')
def stock():
    """Public medicine stock view"""
    medicines = Medicine.query.all()
    low_stock = [m for m in medicines if m.quantity <= m.reorder_level]
    
    return render_template('stock.html',
        medicines=medicines,
        low_stock=low_stock
    )

@app.route('/stock/add', methods=['POST'])
def stock_add():
    """Add medicine (public)"""
    try:
        medicine = Medicine(
            name=request.form.get('name'),
            category=request.form.get('category'),
            quantity=int(request.form.get('quantity',0)),
            reorder_level=int(request.form.get('reorder_level',20)),
            unit_price=float(request.form.get('unit_price',0))
        )
        db.session.add(medicine)
        db.session.commit()
        return redirect(url_for('stock'))
    except Exception as e:
        logger.error(f"Add medicine error: {e}")
        return redirect(url_for('stock'))

@app.route('/stock/update/<int:id>', methods=['POST'])
def stock_update(id):
    """Update stock (public)"""
    medicine = Medicine.query.get_or_404(id)
    medicine.quantity = int(request.form.get('quantity', 0))
    db.session.commit()
    return redirect(url_for('stock'))

@app.route('/stock/delete/<int:id>', methods=['POST'])
def stock_delete(id):
    """Delete medicine (public)"""
    medicine = Medicine.query.get_or_404(id)
    db.session.delete(medicine)
    db.session.commit()
    return redirect(url_for('stock'))

# ── HOSPITAL/ADMIN ROUTES ──────────────────────────────
@app.route('/mgmt/doctors')
@require_login
@require_role('hospital')
def mgmt_doctors():
    doctors = Doctor.query.all()
    return render_template('mgmt_doctors.html', doctors=doctors)

@app.route('/mgmt/doctors/add', methods=['POST'])
@require_login
@require_role('hospital')
def mgmt_add_doctor():
    try:
        email = request.form.get('email','').strip()
        data = {
            'name': request.form.get('name'),
            'specialty': request.form.get('specialty'),
            'password': request.form.get('password'),
            'available_days': request.form.get('available_days','Mon,Tue,Wed,Thu,Fri')
        }
        
        if User.query.filter_by(email=email).first():
            return render_template('mgmt_doctors.html', doctors=Doctor.query.all(), error="Email already exists.")
        u = User(username=email.split('@')[0], email=email, role='doctor',
                 full_name=data['name'], specialization=data['specialty'])
        u.set_password(data['password'])
        db.session.add(u)
        db.session.flush()
        d = Doctor(name=data['name'], specialty=data['specialty'],
                   available_days=data.get('available_days','Mon,Tue,Wed,Thu,Fri'), user_id=u.id)
        db.session.add(d)
        db.session.commit()
        return redirect(url_for('mgmt_doctors'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Add doctor error: {e}")
        return redirect(url_for('mgmt_doctors'))

@app.route('/mgmt/pharmacies')
@require_login
@require_role('hospital')
def mgmt_pharmacies():
    pharmacies = User.query.filter_by(role='pharmacy').all()
    return render_template('mgmt_pharmacies.html', pharmacies=pharmacies,
        success=request.args.get('success'), error=request.args.get('error'))

@app.route('/mgmt/pharmacies/add', methods=['POST'])
@require_login
@require_role('hospital')
def mgmt_add_pharmacy():
    try:
        email = request.form.get('email','').strip()
        name = request.form.get('name','').strip()
        specialization = request.form.get('specialization','Pharmacy').strip()
        password = request.form.get('password','')

        if User.query.filter_by(email=email).first():
            return render_template('mgmt_pharmacies.html', pharmacies=User.query.filter_by(role='pharmacy').all(), error="Email already exists.")

        u = User(username=email.split('@')[0], email=email, role='pharmacy', full_name=name, specialization=specialization)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return redirect(url_for('mgmt_pharmacies', success='Pharmacy staff added successfully.'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Add pharmacy error: {e}")
        return redirect(url_for('mgmt_pharmacies', error='Failed to add pharmacy staff.'))

@app.route('/mgmt/pharmacies/delete/<int:id>', methods=['POST'])
@require_login
@require_role('hospital')
def mgmt_delete_pharmacy(id):
    user = User.query.filter_by(id=id, role='pharmacy').first()
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('mgmt_pharmacies', success='Pharmacy staff removed.'))

@app.route('/mgmt/orders')
@require_login
@require_role('hospital')
def mgmt_orders():
    orders = Order.query.join(Medicine).join(User, Order.patient_id == User.id).order_by(Order.created_at.desc()).all()
    return render_template('mgmt_orders.html', orders=orders)

@app.route('/mgmt/funding')
@require_login
@require_role('hospital')
def mgmt_funding():
    orders = Order.query.filter(Order.status.in_(['delivered','shipped','packing','accepted'])).all()
    total_rev = sum(o.total_price for o in orders)
    med_rev = {}
    for o in orders:
        n = o.medicine.name
        med_rev[n] = med_rev.get(n, {'name':n,'count':0,'revenue':0})
        med_rev[n]['count'] += 1
        med_rev[n]['revenue'] += o.total_price
    breakdown = sorted(med_rev.values(), key=lambda x: x['revenue'], reverse=True)
    docs = Doctor.query.all()
    doc_load = [{'name':d.name,'count':len(d.appointments)} for d in docs]
    return render_template('mgmt_funding.html', total_revenue=total_rev,
        total_orders=Order.query.count(), total_medicines=Medicine.query.count(),
        revenue_breakdown=breakdown, doctor_load=doc_load)

# ── MESSAGES ────────────────────────────────────────────
@app.route('/messages')
@require_login
def messages():
    uid = session.get('user_id')
    role = session.get('role')
    msgs = Message.query.filter(
        (Message.sender_id==uid)|(Message.receiver_id==uid)
    ).order_by(Message.created_at.desc()).limit(30).all()
    
    Message.query.filter_by(receiver_id=uid, is_read=False).update({'is_read':True})
    db.session.commit()
    
    patient_prescriptions = []
    pharmacies = []
    if role == 'doctor':
        contacts = User.query.filter_by(role='patient').all()
    elif role == 'patient':
        contacts = list(User.query.filter_by(role='doctor').all()) + list(User.query.filter_by(role='hospital').all()) + list(User.query.filter_by(role='pharmacy').all())
        patient_prescriptions = Prescription.query.filter_by(patient_id=uid).order_by(Prescription.created_at.desc()).all()
        pharmacies = User.query.filter_by(role='pharmacy').all()
    else:
        contacts = User.query.filter(User.id != uid).all()
    
    selected_id = request.args.get('to', type=int)
    return render_template('messages.html', messages=msgs, contacts=contacts, selected_id=selected_id,
        patient_prescriptions=patient_prescriptions, pharmacies=pharmacies)

@app.route('/messages/send', methods=['POST'])
@require_login
def send_message():
    uid = session.get('user_id')
    try:
        recv_id = int(request.form.get('receiver_id'))
        content = request.form.get('content','').strip()
        
        if not content or len(content) > 5000:
            return redirect(url_for('messages'))
        
        m = Message(sender_id=uid, receiver_id=recv_id, content=content)
        db.session.add(m)
        db.session.commit()
        
        log_activity(uid, "MESSAGE_SENT", f"to_user={recv_id}")
    except Exception as e:
        logger.error(f"Message error: {e}")
    
    return redirect(url_for('messages'))

def parse_frequency(freq_str):
    """Parse frequency string like '2x daily' to get the number of times per day."""
    if not freq_str:
        return 1
    freq_str = freq_str.lower().strip()
    # Common patterns: "2x daily", "3 times a day", "twice daily", etc.
    import re
    # Look for number followed by x or times
    match = re.search(r'(\d+)', freq_str)
    if match:
        return int(match.group(1))
    # Handle words: once=1, twice=2, thrice=3, etc. (rare but possible)
    if 'twice' in freq_str or '2' in freq_str.split()[0] if freq_str.split() else False:
        return 2
    if 'thrice' in freq_str or 'three' in freq_str.split()[0] if freq_str.split() else False:
        return 3
    if 'once' in freq_str or '1' in freq_str.split()[0] if freq_str.split() else False:
        return 1
    # Default to 1 if can't parse
    return 1

@app.route('/patient/send-prescription', methods=['POST'])
@require_login
@require_role('patient')
def patient_send_prescription():
    user_id = session.get('user_id')
    try:
        prescription_id = int(request.form.get('prescription_id', 0))
        pharmacy_id = int(request.form.get('pharmacy_id', 0))
        address = request.form.get('pharmacy_address', '').strip()

        if not prescription_id or not pharmacy_id or not address:
            return redirect(url_for('messages', error='Please select a prescription, pharmacy and address.'))

        prescription = Prescription.query.get(prescription_id)
        if not prescription or prescription.patient_id != user_id:
            return redirect(url_for('messages', error='Prescription not found.'))

        pharmacy_user = User.query.filter_by(id=pharmacy_id, role='pharmacy').first()
        if not pharmacy_user:
            return redirect(url_for('messages', error='Invalid pharmacy selected.'))

        if not prescription.medicines:
            return redirect(url_for('messages', error='Prescription contains no medicines.'))

        order_count = 0
        for item in prescription.medicines:
            med_id = item.get('medicine_id')
            medicine = Medicine.query.get(med_id)
            if not medicine:
                continue
            frequency_num = parse_frequency(item.get('frequency', '1x daily'))
            days = int(item.get('days', 1))
            quantity = frequency_num * days
            quantity = quantity if quantity > 0 else 1
            order = Order(
                patient_id=user_id,
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                quantity=quantity,
                total_price=medicine.unit_price * quantity,
                address=address,
                status='pending'
            )
            db.session.add(order)
            order_count += 1

        if order_count == 0:
            return redirect(url_for('messages', error='No valid medicines found in prescription.'))

        note = f"Prescription #{prescription.id} sent to pharmacy. Address: {address}"
        msg = Message(sender_id=user_id, receiver_id=pharmacy_id, content=note)
        db.session.add(msg)
        db.session.commit()
        log_activity(user_id, "SEND_PRESCRIPTION_PHARMACY", f"pharmacy_id={pharmacy_id}, prescription_id={prescription.id}, orders={order_count}")
        return redirect(url_for('messages', success='Prescription sent to pharmacy successfully.'))
    except Exception as e:
        logger.error(f"Send prescription error: {e}")
        db.session.rollback()
        return redirect(url_for('messages', error='Unable to send prescription to pharmacy.'))

@app.route('/chatbot')
def chatbot():
    """Dedicated chatbot page"""
    return render_template('chatbot.html')

# ── AI APIs ─────────────────────────────────────────────
@app.route('/api/suggest-doctor', methods=['POST'])
def suggest_doctor():
    symptoms = request.json.get('symptoms','')
    docs = Doctor.query.all()
    doc_list = "\n".join([f"- {d.name} ({d.specialty})" for d in docs])
    prompt = f"Patient symptoms: {symptoms}\nDoctors:\n{doc_list}\nReturn ONLY JSON:\n{{\"doctor_name\":\"...\",\"specialty\":\"...\",\"reason\":\"...\",\"urgency\":\"Low/Medium/High\"}}"
    
    text = ai(prompt)
    if "```" in text:
        text = text.split("```")[1].replace("json","").strip()
    
    try:
        r = json.loads(text)
        r.setdefault("urgency","Medium")
        r.setdefault("specialty","General Physician")
        r.setdefault("reason","Based on your symptoms")
    except:
        r = {"doctor_name":"Dr. Priya Sharma","specialty":"General Physician","reason":"Recommended for your symptoms","urgency":"Medium"}
    
    return jsonify(r)

@app.route('/api/ai-reorder', methods=['POST'])
def ai_reorder():
    low = Medicine.query.filter(Medicine.quantity<=Medicine.reorder_level).all()
    if not low:
        return jsonify({"message":"All medicines well-stocked!","items":[]})
    items_text = "\n".join([f"- {m.name}: qty={m.quantity}, reorder={m.reorder_level}" for m in low])
    text = ai(f"Pharmacy low stock:\n{items_text}\nReturn ONLY JSON array:\n[{{\"name\":\"...\",\"reorder_qty\":50,\"priority\":\"High\",\"reason\":\"...\"}}]")
    if "```" in text:
        text = text.split("```")[1].replace("json","").strip()
    try:
        suggestions = json.loads(text)
    except:
        return jsonify({"error":"AI parsing failed","items":[]})
    return jsonify({"message":f"{len(low)} items need reordering","items":suggestions})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('message','')
    history = data.get('history',[])
    role = session.get('role','')
    uid = session.get('user_id')
    
    if not msg.strip():
        return jsonify({"reply":"Please enter a message."})

    meds = Medicine.query.all()
    med_list = ", ".join([f"{m.name}(₹{m.unit_price},qty:{m.quantity})" for m in meds])
    docs = Doctor.query.all()
    doc_list = ", ".join([f"{d.name}({d.specialty})" for d in docs])

    if role == 'doctor':
        sys_prompt = f"You are a SmartClinic AI for Dr. {session.get('full_name','')}. Help with patient management, appointments. Be professional."
    elif role == 'pharmacy':
        sys_prompt = f"You are SmartClinic pharmacy AI. Help with stock, orders. Current medicines: {med_list}."
    elif role == 'hospital':
        sys_prompt = f"You are hospital management AI. Help with doctor management, shipments. Doctors: {doc_list}."
    elif role == 'patient':
        sys_prompt = f"You are SmartClinic AI for patient {session.get('full_name','')}. Help book appointments, order medicines. Available doctors: {doc_list}. Available medicines: {med_list}."
    else:
        sys_prompt = f"You are SmartClinic AI assistant. Doctors: {doc_list}. Medicines: {med_list}. Be helpful."

    messages = [{"role":"system","content":sys_prompt}]
    for m in history[-6:]:
        messages.append(m)
    messages.append({"role":"user","content":msg})

    try:
        r = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, max_tokens=300)
        reply = r.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"reply":"Something went wrong. Please try again."})

# ── ERROR HANDLERS ──────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)