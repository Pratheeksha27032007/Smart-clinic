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
    return True, ""

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_appointment_date(date_str):
    """Ensure appointment is in future"""
    try:
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if appt_date < date.today():
            return False, "Appointment date must be in the future"
        return True, ""
    except:
        return False, "Invalid date format"

def log_activity(user_id, action, details=None):
    """Log user actions for audit trail"""
    try:
        log = ActivityLog(user_id=user_id, action=action, details=details)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
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

def ai(prompt):
    """Call Groq API for AI responses"""
    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role":"system","content":"You are a helpful SmartClinic assistant. Be concise."},
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

def seed_data():
    """Seed initial data"""
    presets = [
        {"email":"doctor@smartclinic.com","username":"doctor1","role":"doctor","full_name":"Dr. Priya Sharma","specialization":"General Physician","password":"Doctor@123"},
        {"email":"pharmacy@smartclinic.com","username":"pharmacy1","role":"pharmacy","full_name":"Pharmacy Staff","specialization":"Pharmacy","password":"Pharma@123"},
        {"email":"admin@smartclinic.com","username":"admin1","role":"hospital","full_name":"Hospital Admin","specialization":"Management","password":"Admin@123"},
    ]
    
    for p in presets:
        if not User.query.filter_by(email=p['email']).first():
            u = User(username=p['username'],email=p['email'],role=p['role'],
                    full_name=p['full_name'],specialization=p['specialization'])
            u.set_password(p['password'])
            db.session.add(u)

    if Doctor.query.count() == 0:
        doc_user = User.query.filter_by(email='doctor@smartclinic.com').first()
        doctors = [
            Doctor(name="Dr. Priya Sharma", specialty="General Physician", available_days="Mon,Tue,Wed,Thu,Fri", user_id=doc_user.id if doc_user else None),
            Doctor(name="Dr. Arjun Mehta", specialty="Cardiologist", available_days="Mon,Wed,Fri"),
            Doctor(name="Dr. Sneha Patel", specialty="Dermatologist", available_days="Tue,Thu,Sat"),
            Doctor(name="Dr. Rahul Verma", specialty="Orthopedic", available_days="Mon,Tue,Thu,Fri"),
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
        
        return render_template('login.html', error='Invalid credentials or wrong role selected.')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip()
        pwd = request.form.get('password','')
        full_name = request.form.get('full_name','').strip()
        phone = request.form.get('phone','').strip()
        age = request.form.get('age','')
        blood = request.form.get('blood_group','').strip()
        
        errors = []
        
        if not validate_email(email):
            errors.append('Invalid email format')
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')
        
        valid_pwd, pwd_msg = validate_password(pwd)
        if not valid_pwd:
            errors.append(pwd_msg)
        
        if errors:
            return render_template('register.html', error=' | '.join(errors))
        
        try:
            u = User(username=username, email=email, role='patient', full_name=full_name,
                    phone=phone, age=int(age) if age else None, blood_group=blood)
            u.set_password(pwd)
            db.session.add(u)
            db.session.flush()
            
            profile = PatientProfile(user_id=u.id)
            db.session.add(profile)
            db.session.commit()
            
            log_activity(u.id, "PATIENT_REGISTRATION")
            return render_template('register.html', success='Account created! You can now login.')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return render_template('register.html', error='Registration failed')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    log_activity(user_id, "LOGOUT")
    session.clear()
    return redirect(url_for('login'))

# ── MAIN DASHBOARD ──────────────────────────────────────
@app.route('/')
def index():
    role = session.get('role','')
    uid = session.get('user_id')
    tod = time_of_day()
    today = date.today().isoformat()

    if role == 'doctor':
        try:
            doc = Doctor.query.filter_by(user_id=uid).first()
            doc_id = doc.id if doc else None
            todays = Appointment.query.filter_by(doctor_id=doc_id, appointment_date=today).all() if doc_id else []
            pending = Appointment.query.filter_by(doctor_id=doc_id, status='pending').count() if doc_id else 0
            accepted = Appointment.query.filter_by(doctor_id=doc_id, status='accepted', appointment_date=today).count() if doc_id else 0
            unread = Message.query.filter_by(receiver_id=uid, is_read=False).count()
            msgs = Message.query.filter((Message.sender_id==uid)|(Message.receiver_id==uid)).order_by(Message.created_at.desc()).limit(5).all()
            
            return render_template('index.html', role=role, time_of_day=tod,
                today_appts=len(todays), pending_appts=pending, accepted_appts=accepted,
                unread_msgs=unread, todays_list=todays, recent_msgs=msgs)
        except Exception as e:
            logger.error(f"Error: {e}")
            return render_template('index.html', role=role, error="Error loading dashboard")

    elif role == 'pharmacy':
        try:
            meds = Medicine.query.all()
            low = [m for m in meds if m.quantity <= m.reorder_level]
            pend_ord = Order.query.filter_by(status='pending').all()
            delivered = Order.query.filter_by(status='delivered').count()
            return render_template('index.html', role=role, time_of_day=tod,
                total_meds=len(meds), low_stock=len(low), pending_orders=len(pend_ord),
                delivered_today=delivered, orders_list=pend_ord[:5], low_stock_list=low[:5])
        except Exception as e:
            logger.error(f"Error: {e}")
            return render_template('index.html', role=role, error="Error loading dashboard")

    elif role == 'hospital':
        try:
            docs = Doctor.query.all()
            patients = User.query.filter_by(role='patient').count()
            orders = Order.query.count()
            shipping = Order.query.filter_by(status='shipped').count()
            recent = Order.query.order_by(Order.created_at.desc()).limit(5).all()
            return render_template('index.html', role=role, time_of_day=tod,
                total_doctors=len(docs), total_patients=patients, total_orders=orders,
                shipping_orders=shipping, doctors_list=docs, recent_shipments=recent)
        except Exception as e:
            logger.error(f"Error: {e}")
            return render_template('index.html', role=role, error="Error loading dashboard")

    elif role == 'patient':
        try:
            my_appts = Appointment.query.filter_by(patient_user_id=uid).count()
            my_orders = Order.query.filter_by(patient_id=uid).count()
            accepted = Appointment.query.filter_by(patient_user_id=uid, status='accepted').count()
            in_transit = Order.query.filter_by(patient_id=uid, status='shipped').count()
            return render_template('index.html', role=role, time_of_day=tod,
                my_appts=my_appts, my_orders=my_orders, accepted=accepted, in_transit=in_transit)
        except Exception as e:
            logger.error(f"Error: {e}")
            return render_template('index.html', role=role, error="Error loading dashboard")

    return render_template('index.html', role=role, time_of_day=tod,
        total_medicines=Medicine.query.count(),
        low_stock=Medicine.query.filter(Medicine.quantity<=Medicine.reorder_level).count(),
        total_doctors=Doctor.query.count(),
        today_appointments=Appointment.query.filter_by(appointment_date=today).count())

# ── PATIENT PROFILE ─────────────────────────────────────
@app.route('/patient/profile', methods=['GET','POST'])
@require_login
def patient_profile():
    uid = session.get('user_id')
    user = User.query.get(uid)
    profile = PatientProfile.query.filter_by(user_id=uid).first()
    
    if not profile:
        profile = PatientProfile(user_id=uid)
        db.session.add(profile)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            profile.allergies = request.form.get('allergies', '').strip()
            profile.chronic_conditions = request.form.get('chronic_conditions', '').strip()
            profile.emergency_contact = request.form.get('emergency_contact', '').strip()
            profile.emergency_phone = request.form.get('emergency_phone', '').strip()
            profile.insurance_provider = request.form.get('insurance_provider', '').strip()
            profile.insurance_id = request.form.get('insurance_id', '').strip()
            db.session.commit()
            log_activity(uid, "PROFILE_UPDATE")
            return render_template('patient_profile.html', user=user, profile=profile, success='Profile updated!')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error: {e}")
            return render_template('patient_profile.html', user=user, profile=profile, error='Update failed')
    
    return render_template('patient_profile.html', user=user, profile=profile)

# ── PATIENT APPOINTMENTS ────────────────────────────────
@app.route('/patient/appointments', methods=['GET','POST'])
@require_login
def patient_appointments():
    uid = session.get('user_id')
    
    if request.method == 'POST':
        try:
            doctor_id = int(request.form.get('doctor_id'))
            appt_date = request.form.get('appointment_date')
            appt_time = request.form.get('appointment_time')
            symptoms = request.form.get('symptoms', '').strip()
            
            valid, msg = validate_appointment_date(appt_date)
            if not valid:
                return render_template('patient_appointments.html', 
                    appointments=Appointment.query.filter_by(patient_user_id=uid).all(),
                    doctors=Doctor.query.all(), today=date.today().isoformat(), error=msg)
            
            user = User.query.get(uid)
            appt = Appointment(
                patient_name=user.full_name or user.username,
                patient_age=user.age or 0,
                symptoms=symptoms,
                doctor_id=doctor_id,
                appointment_date=appt_date,
                appointment_time=appt_time,
                patient_user_id=uid,
                status='pending'
            )
            db.session.add(appt)
            db.session.commit()
            log_activity(uid, "APPOINTMENT_BOOKED")
            return redirect(url_for('patient_appointments'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error: {e}")
            return render_template('patient_appointments.html',
                appointments=Appointment.query.filter_by(patient_user_id=uid).all(),
                doctors=Doctor.query.all(), today=date.today().isoformat(), error='Booking failed')
    
    appts = Appointment.query.filter_by(patient_user_id=uid).order_by(Appointment.appointment_date.desc()).all()
    docs = Doctor.query.all()
    return render_template('patient_appointments.html', 
        appointments=appts, doctors=docs, today=date.today().isoformat())

@app.route('/patient/cancel/<int:id>', methods=['POST'])
@require_login
def patient_cancel(id):
    try:
        a = Appointment.query.get_or_404(id)
        db.session.delete(a)
        db.session.commit()
        log_activity(session.get('user_id'), "APPOINTMENT_CANCELLED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(url_for('patient_appointments'))

# ── DOCTOR APPOINTMENTS ─────────────────────────────────
@app.route('/doctor/appointments')
@require_role('doctor')
def doctor_appointments():
    uid = session.get('user_id')
    doc = Doctor.query.filter_by(user_id=uid).first()
    f = request.args.get('filter','all')
    q = Appointment.query.filter_by(doctor_id=doc.id) if doc else Appointment.query.filter_by(doctor_id=-1)
    if f == 'pending':
        q = q.filter_by(status='pending')
    elif f == 'accepted':
        q = q.filter_by(status='accepted')
    elif f == 'today':
        q = q.filter_by(appointment_date=date.today().isoformat())
    appts = q.order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    pending_count = Appointment.query.filter_by(doctor_id=doc.id if doc else -1, status='pending').count()
    return render_template('doctor_appointments.html', appointments=appts, doctor=doc, filter=f, pending_count=pending_count)

@app.route('/doctor/accept/<int:id>', methods=['POST'])
@require_role('doctor')
def doctor_accept(id):
    try:
        a = Appointment.query.get_or_404(id)
        a.status = 'accepted'
        db.session.commit()
        log_activity(session.get('user_id'), "APPOINTMENT_ACCEPTED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(request.referrer or url_for('doctor_appointments'))

@app.route('/doctor/decline/<int:id>', methods=['POST'])
@require_role('doctor')
def doctor_decline(id):
    try:
        a = Appointment.query.get_or_404(id)
        a.status = 'declined'
        db.session.commit()
        log_activity(session.get('user_id'), "APPOINTMENT_DECLINED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(request.referrer or url_for('doctor_appointments'))

# ── DOCTOR PRESCRIPTIONS ────────────────────────────────
@app.route('/doctor/prescriptions', methods=['GET','POST'])
@require_role('doctor')
def doctor_prescriptions():
    uid = session.get('user_id')
    doc = Doctor.query.filter_by(user_id=uid).first()
    
    if request.method == 'POST':
        try:
            patient_id = int(request.form.get('patient_id'))
            medicines_json = request.form.get('medicines')
            instructions = request.form.get('instructions', '').strip()
            
            medicines = json.loads(medicines_json)
            
            prescription = Prescription(
                doctor_id=doc.id,
                patient_id=patient_id,
                medicines=medicines,
                instructions=instructions,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(prescription)
            db.session.commit()
            log_activity(uid, "PRESCRIPTION_CREATED")
            return redirect(url_for('doctor_prescriptions'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error: {e}")
    
    prescriptions = Prescription.query.filter_by(doctor_id=doc.id).order_by(Prescription.created_at.desc()).all() if doc else []
    patients = User.query.filter_by(role='patient').all()
    medicines = Medicine.query.all()
    
    return render_template('doctor_prescriptions.html', 
        prescriptions=prescriptions, patients=patients, medicines=medicines)

# ── PATIENT MEDICINES ──────────────────────────────────
@app.route('/patient/medicines')
@require_login
def patient_medicines():
    meds = Medicine.query.all()
    return render_template('patient_medicines.html', medicines=meds)

@app.route('/patient/order', methods=['POST'])
@require_login
def patient_order():
    uid = session.get('user_id')
    data = request.form
    try:
        med = Medicine.query.get_or_404(int(data['medicine_id']))
        qty = int(data.get('quantity',1))
        
        if med.quantity < qty:
            meds = Medicine.query.all()
            return render_template('patient_medicines.html', medicines=meds, error="Not enough stock.")
        
        o = Order(patient_id=uid, medicine_id=med.id, quantity=qty,
                  total_price=qty*med.unit_price, address=data.get('address',''), status='pending')
        db.session.add(o)
        db.session.commit()
        log_activity(uid, "ORDER_PLACED")
        return render_template('patient_medicines.html', medicines=Medicine.query.all(), success="Order placed successfully!")
    except Exception as e:
        logger.error(f"Error: {e}")
        return render_template('patient_medicines.html', medicines=Medicine.query.all(), error="Order failed")

@app.route('/patient/orders')
@require_login
def patient_orders():
    uid = session.get('user_id')
    orders = Order.query.filter_by(patient_id=uid).order_by(Order.created_at.desc()).all()
    return render_template('patient_orders.html', orders=orders)

# ── PHARMACY ROUTES ────────────────────────────────────
@app.route('/pharmacy/stock')
@require_role('pharmacy')
def pharmacy_stock():
    meds = Medicine.query.all()
    low = [m for m in meds if m.quantity <= m.reorder_level]
    return render_template('pharmacy_stock.html', medicines=meds, low_stock=low)

@app.route('/pharmacy/stock/add', methods=['POST'])
@require_role('pharmacy')
def pharmacy_add_medicine():
    try:
        data = request.form
        med = Medicine(name=data['name'], category=data['category'],
                    quantity=int(data['quantity']), reorder_level=int(data['reorder_level']),
                    unit_price=float(data['unit_price']))
        db.session.add(med)
        db.session.commit()
        log_activity(session.get('user_id'), "MEDICINE_ADDED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(url_for('pharmacy_stock'))

@app.route('/pharmacy/stock/update/<int:id>', methods=['POST'])
@require_role('pharmacy')
def pharmacy_update_stock(id):
    try:
        m = Medicine.query.get_or_404(id)
        m.quantity = int(request.form['quantity'])
        db.session.commit()
        log_activity(session.get('user_id'), "STOCK_UPDATED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(url_for('pharmacy_stock'))

@app.route('/pharmacy/orders')
@require_role('pharmacy')
def pharmacy_orders():
    f = request.args.get('filter','all')
    q = Order.query
    if f != 'all':
        q = q.filter_by(status=f)
    orders = q.order_by(Order.created_at.desc()).all()
    return render_template('pharmacy_orders.html', orders=orders, filter=f)

@app.route('/pharmacy/accept-order/<int:id>', methods=['POST'])
@require_role('pharmacy')
def pharmacy_accept_order(id):
    try:
        o = Order.query.get_or_404(id)
        o.status='accepted'
        db.session.commit()
        log_activity(session.get('user_id'), "ORDER_ACCEPTED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(request.referrer or url_for('pharmacy_orders'))

@app.route('/pharmacy/pack-order/<int:id>', methods=['POST'])
@require_role('pharmacy')
def pharmacy_pack_order(id):
    try:
        o = Order.query.get_or_404(id)
        o.status='packing'
        m = Medicine.query.get(o.medicine_id)
        if m:
            m.quantity = max(0, m.quantity - o.quantity)
        db.session.commit()
        log_activity(session.get('user_id'), "ORDER_PACKING")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(request.referrer or url_for('pharmacy_orders'))

@app.route('/pharmacy/ship-order/<int:id>', methods=['POST'])
@require_role('pharmacy')
def pharmacy_ship_order(id):
    try:
        o = Order.query.get_or_404(id)
        o.status='shipped'
        db.session.commit()
        log_activity(session.get('user_id'), "ORDER_SHIPPED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(request.referrer or url_for('pharmacy_orders'))

# ── MESSAGES ───────────────────────────────────────────
@app.route('/messages')
@require_login
def messages():
    uid = session.get('user_id')
    role = session.get('role')
    msgs = Message.query.filter((Message.sender_id==uid)|(Message.receiver_id==uid)).order_by(Message.created_at.desc()).limit(30).all()
    Message.query.filter_by(receiver_id=uid, is_read=False).update({'is_read':True})
    db.session.commit()
    
    if role == 'doctor':
        contacts = User.query.filter_by(role='patient').all()
    elif role == 'patient':
        contacts = list(User.query.filter_by(role='doctor').all()) + list(User.query.filter_by(role='hospital').all())
    else:
        contacts = User.query.filter(User.id != uid).all()
    
    selected_id = request.args.get('to', type=int)
    return render_template('messages.html', messages=msgs, contacts=contacts, selected_id=selected_id)

@app.route('/messages/send', methods=['POST'])
@require_login
def send_message():
    uid = session.get('user_id')
    try:
        recv_id = int(request.form.get('receiver_id'))
        content = request.form.get('content','').strip()
        
        if content and len(content) <= 5000:
            m = Message(sender_id=uid, receiver_id=recv_id, content=content)
            db.session.add(m)
            db.session.commit()
            log_activity(uid, "MESSAGE_SENT")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    return redirect(url_for('messages'))

# ── HOSPITAL MANAGEMENT ────────────────────────────────
@app.route('/mgmt/doctors')
@require_role('hospital')
def mgmt_doctors():
    docs = Doctor.query.all()
    return render_template('mgmt_doctors.html', doctors=docs, success=request.args.get('success'))

@app.route('/mgmt/doctors/add', methods=['POST'])
@require_role('hospital')
def mgmt_add_doctor():
    try:
        data = request.form
        email = data.get('email','')
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
        log_activity(session.get('user_id'), "DOCTOR_ADDED")
        return redirect(url_for('mgmt_doctors', success='Doctor added successfully!'))
    except Exception as e:
        logger.error(f"Error: {e}")
        return render_template('mgmt_doctors.html', doctors=Doctor.query.all(), error="Failed to add doctor")

@app.route('/mgmt/orders')
@require_role('hospital')
def mgmt_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('mgmt_orders.html', orders=orders)

@app.route('/mgmt/deliver/<int:id>', methods=['POST'])
@require_role('hospital')
def mgmt_deliver(id):
    try:
        o = Order.query.get_or_404(id)
        o.status='delivered'
        o.delivered_at = datetime.utcnow()
        db.session.commit()
        log_activity(session.get('user_id'), "ORDER_DELIVERED")
    except Exception as e:
        logger.error(f"Error: {e}")
    return redirect(url_for('mgmt_orders'))

@app.route('/mgmt/funding')
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

# ── AI APIs ────────────────────────────────────────────
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
    med_list = ", ".join([f"{m.name}(₹{m.unit_price})" for m in meds])
    docs = Doctor.query.all()
    doc_list = ", ".join([f"{d.name}({d.specialty})" for d in docs])

    if role == 'doctor':
        sys_prompt = f"You are a SmartClinic AI for Dr. {session.get('full_name','')}. Help with patient management. Be concise."
    elif role == 'pharmacy':
        sys_prompt = f"You are SmartClinic pharmacy AI. Help with stock and orders."
    elif role == 'hospital':
        sys_prompt = f"You are hospital management AI. Help with operations."
    elif role == 'patient':
        sys_prompt = f"You are SmartClinic AI for patient {session.get('full_name','')}. Help book appointments and order medicines."
    else:
        sys_prompt = f"You are SmartClinic AI assistant. Be helpful and concise."

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)