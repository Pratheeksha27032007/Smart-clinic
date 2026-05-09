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
            Doctor(name="Dr. Priya Sharma", specialty="General Physician", available_days="Mon,Tue,Wed,Thu,Fri", user_id=doc_user.id if doc_user else None, consultation_fee=500),
            Doctor(name="Dr. Arjun Mehta", specialty="Cardiologist", available_days="Mon,Wed,Fri", consultation_fee=800),
            Doctor(name="Dr. Sneha Patel", specialty="Dermatologist", available_days="Tue,Thu,Sat", consultation_fee=600),
            Doctor(name="Dr. Rahul Verma", specialty="Orthopedic", available_days="Mon,Tue,Thu,Fri", consultation_fee=700),
        ]
        db.session.add_all(doctors)

    if Medicine.query.count() == 0:
        medicines = [
            Medicine(name="Paracetamol 500mg", category="Analgesic", quantity=120, reorder_level=30, unit_price=2.5, side_effects="Mild headache possible"),
            Medicine(name="Amoxicillin 250mg", category="Antibiotic", quantity=18, reorder_level=25, unit_price=8.0, contraindications="Not for penicillin allergic"),
            Medicine(name="Cetirizine 10mg", category="Antihistamine", quantity=60, reorder_level=20, unit_price=3.0),
            Medicine(name="Metformin 500mg", category="Antidiabetic", quantity=200, reorder_level=50, unit_price=4.5),
            Medicine(name="Omeprazole 20mg", category="Antacid", quantity=12, reorder_level=20, unit_price=6.0),
            Medicine(name="Ibuprofen 400mg", category="NSAID", quantity=75, reorder_level=30, unit_price=3.5, contraindications="Avoid if stomach ulcer"),
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
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip()
        pwd = request.form.get('password','')
        full_name = request.form.get('full_name','').strip()
        phone = request.form.get('phone','').strip()
        age = request.form.get('age','')
        blood = request.form.get('blood_group','').strip()
        
        # Validate inputs
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters')
        
        if not validate_email(email):
            errors.append('Invalid email format')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')
        
        valid_pwd, pwd_msg = validate_password(pwd)
        if not valid_pwd:
            errors.append(pwd_msg)
        
        if phone and not validate_phone(phone):
            errors.append('Invalid phone number')
        
        if errors:
            return render_template('register.html', error=' | '.join(errors))
        
        try:
            u = User(
                username=username,
                email=email,
                role='patient',
                full_name=full_name,
                phone=phone,
                age=int(age) if age else None,
                blood_group=blood
            )
            u.set_password(pwd)
            db.session.add(u)
            db.session.flush()
            
            # Create patient profile
            profile = PatientProfile(user_id=u.id)
            db.session.add(profile)
            db.session.commit()
            
            log_activity(u.id, "PATIENT_REGISTRATION")
            return render_template('register.html', success='Account created! You can now login.')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return render_template('register.html', error='Registration failed. Please try again.')
    
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
            logger.error(f"Doctor dashboard error: {e}")
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
            logger.error(f"Pharmacy dashboard error: {e}")
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
            logger.error(f"Hospital dashboard error: {e}")
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
            logger.error(f"Patient dashboard error: {e}")
            return render_template('index.html', role=role, error="Error loading dashboard")

    return render_template('index.html', role=role, time_of_day=tod,
        total_medicines=Medicine.query.count(),
        low_stock=Medicine.query.filter(Medicine.quantity<=Medicine.reorder_level).count(),
        total_doctors=Doctor.query.count(),
        today_appointments=Appointment.query.filter_by(appointment_date=today).count())

# ── PATIENT PROFILE ─────────────────────────────────────
@app.route('/patient/profile', methods=['GET','POST'])
@require_role('patient')
def patient_profile():
    uid = session.get('user_id')
    user = User.query.get(uid)
    profile = PatientProfile.query.filter_by(user_id=uid).first()
    
    if request.method == 'POST':
        try:
            if not profile:
                profile = PatientProfile(user_id=uid)
            
            profile.allergies = request.form.get('allergies', '').strip()
            profile.chronic_conditions = request.form.get('chronic_conditions', '').strip()
            profile.emergency_contact = request.form.get('emergency_contact', '').strip()
            profile.emergency_phone = request.form.get('emergency_phone', '').strip()
            profile.insurance_provider = request.form.get('insurance_provider', '').strip()
            profile.insurance_id = request.form.get('insurance_id', '').strip()
            
            db.session.add(profile)
            db.session.commit()
            
            log_activity(uid, "PROFILE_UPDATE")
            return render_template('patient_profile.html', user=user, profile=profile, success='Profile updated!')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {e}")
            return render_template('patient_profile.html', user=user, profile=profile, error='Update failed')
    
    return render_template('patient_profile.html', user=user, profile=profile)

# ── APPOINTMENTS ────────────────────────────────────────
@app.route('/patient/appointments')
@require_role('patient')
def patient_appointments():
    uid = session.get('user_id')
    appts = Appointment.query.filter_by(patient_user_id=uid).order_by(Appointment.appointment_date.desc()).all()
    docs = Doctor.query.all()
    return render_template('patient_appointments.html', 
        appointments=appts, doctors=docs, today=date.today().isoformat())

@app.route('/patient/book', methods=['POST'])
@require_role('patient')
def patient_book():
    uid = session.get('user_id')
    user = User.query.get(uid)
    data = request.form
    
    try:
        # Validation
        doctor_id = int(data.get('doctor_id'))
        appt_date = data.get('appointment_date')
        appt_time = data.get('appointment_time')
        symptoms = data.get('symptoms', '').strip()
        
        # Validate date
        valid, msg = validate_appointment_date(appt_date)
        if not valid:
            return jsonify({'error': msg}), 400
        
        # Check for conflicts (prevent double-booking)
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status='accepted'
        ).first()
        
        if existing:
            return jsonify({'error': 'This time slot is already booked'}), 400
        
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
        
        log_activity(uid, "APPOINTMENT_BOOKED", f"doctor_id={doctor_id}")
        return jsonify({'success': 'Appointment booked successfully!'}), 200
    except ValueError as e:
        return jsonify({'error': 'Invalid input format'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Booking error: {e}")
        return jsonify({'error': 'Booking failed'}), 500

# ── PRESCRIPTIONS ───────────────────────────────────────
@app.route('/doctor/prescriptions', methods=['GET','POST'])
@require_role('doctor')
def doctor_prescriptions():
    uid = session.get('user_id')
    doc = Doctor.query.filter_by(user_id=uid).first()
    
    if request.method == 'POST':
        try:
            patient_id = int(request.form.get('patient_id'))
            medicines_json = request.form.get('medicines')  # JSON string
            instructions = request.form.get('instructions', '').strip()
            
            medicines = json.loads(medicines_json)
            
            # Validate medicines exist
            for med in medicines:
                m = Medicine.query.get(med.get('medicine_id'))
                if not m:
                    return jsonify({'error': f'Medicine not found'}), 400
            
            prescription = Prescription(
                doctor_id=doc.id,
                patient_id=patient_id,
                medicines=medicines,
                instructions=instructions,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(prescription)
            db.session.commit()
            
            log_activity(uid, "PRESCRIPTION_CREATED", f"patient_id={patient_id}")
            return jsonify({'success': 'Prescription created!'}), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Prescription error: {e}")
            return jsonify({'error': str(e)}), 500
    
    prescriptions = Prescription.query.filter_by(doctor_id=doc.id).order_by(Prescription.created_at.desc()).all()
    patients = User.query.filter_by(role='patient').all()
    medicines = Medicine.query.all()
    
    return render_template('doctor_prescriptions.html', 
        prescriptions=prescriptions, patients=patients, medicines=medicines)

# ── MESSAGES ────────────────────────────────────────────
@app.route('/messages')
def messages():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    
    role = session.get('role')
    msgs = Message.query.filter(
        (Message.sender_id==uid)|(Message.receiver_id==uid)
    ).order_by(Message.created_at.desc()).limit(30).all()
    
    Message.query.filter_by(receiver_id=uid, is_read=False).update({'is_read':True})
    db.session.commit()
    
    if role == 'doctor':
        contacts = User.query.filter_by(role='patient').all()
    elif role == 'patient':
        contacts = User.query.filter_by(role='doctor').all()
        contacts += User.query.filter_by(role='hospital').all()
    else:
        contacts = User.query.filter(User.id != uid).all()
    
    selected_id = request.args.get('to', type=int)
    return render_template('messages.html', messages=msgs, contacts=contacts, selected_id=selected_id)

@app.route('/messages/send', methods=['POST'])
def send_message():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    
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
        user = User.query.get(uid)
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)