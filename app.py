from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from database import db, Medicine, Appointment, Doctor, User
from datetime import datetime, date
from groq import Groq
import json, os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartclinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'smartclinic-secret-2024')
db.init_app(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ai(prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful SmartClinic medical assistant. Be concise."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("AI ERROR:", e)
        return "Sorry, AI service is temporarily unavailable."

def seed_data():
    if Doctor.query.count() == 0:
        doctors = [
            Doctor(name="Dr. Priya Sharma",  specialty="General Physician", available_days="Mon,Tue,Wed,Thu,Fri"),
            Doctor(name="Dr. Arjun Mehta",   specialty="Cardiologist",      available_days="Mon,Wed,Fri"),
            Doctor(name="Dr. Sneha Patel",   specialty="Dermatologist",     available_days="Tue,Thu,Sat"),
            Doctor(name="Dr. Rahul Verma",   specialty="Orthopedic",        available_days="Mon,Tue,Thu,Fri"),
        ]
        db.session.add_all(doctors)
    if Medicine.query.count() == 0:
        medicines = [
            Medicine(name="Paracetamol 500mg", category="Analgesic",     quantity=120, reorder_level=30, unit_price=2.5),
            Medicine(name="Amoxicillin 250mg", category="Antibiotic",    quantity=18,  reorder_level=25, unit_price=8.0),
            Medicine(name="Cetirizine 10mg",   category="Antihistamine", quantity=60,  reorder_level=20, unit_price=3.0),
            Medicine(name="Metformin 500mg",   category="Antidiabetic",  quantity=200, reorder_level=50, unit_price=4.5),
            Medicine(name="Omeprazole 20mg",   category="Antacid",       quantity=12,  reorder_level=20, unit_price=6.0),
            Medicine(name="Ibuprofen 400mg",   category="NSAID",         quantity=75,  reorder_level=30, unit_price=3.5),
            Medicine(name="Azithromycin 500mg",category="Antibiotic",    quantity=8,   reorder_level=15, unit_price=12.0),
        ]
        db.session.add_all(medicines)
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_data()

# ── AUTH ──────────────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        role     = request.form.get('role','doctor')
        user = User.query.filter_by(email=email, role=role).first()
        if user and user.check_password(password):
            session['user_id']  = user.id
            session['username'] = user.username
            session['role']     = user.role
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid email, password, or role.')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username  = request.form.get('username','').strip()
        email     = request.form.get('email','').strip()
        password  = request.form.get('password','')
        role      = request.form.get('role','doctor')
        full_name = request.form.get('full_name','').strip()
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters.')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered.')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already taken.')
        extra = request.form.get("extra","").strip()
        user = User(username=username, email=email, role=role, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return render_template('register.html', success='Account created! You can now login.')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── DASHBOARD ─────────────────────────────────────────────────
@app.route('/')
def index():
    total_medicines = Medicine.query.count()
    low_stock       = Medicine.query.filter(Medicine.quantity <= Medicine.reorder_level).count()
    total_doctors   = Doctor.query.count()
    today_str       = date.today().isoformat()
    today_appts     = Appointment.query.filter_by(appointment_date=today_str).count()
    return render_template('index.html', total_medicines=total_medicines, low_stock=low_stock,
                           total_doctors=total_doctors, today_appointments=today_appts)

# ── STOCK ──────────────────────────────────────────────────────
@app.route('/stock')
def stock():
    medicines = Medicine.query.all()
    low_stock = [m for m in medicines if m.quantity <= m.reorder_level]
    return render_template('stock.html', medicines=medicines, low_stock=low_stock)

@app.route('/stock/add', methods=['POST'])
def add_medicine():
    data = request.form
    med  = Medicine(name=data['name'], category=data['category'],
                    quantity=int(data['quantity']), reorder_level=int(data['reorder_level']),
                    unit_price=float(data['unit_price']))
    db.session.add(med)
    db.session.commit()
    return redirect(url_for('stock'))

@app.route('/stock/update/<int:med_id>', methods=['POST'])
def update_stock(med_id):
    med = Medicine.query.get_or_404(med_id)
    med.quantity = int(request.form['quantity'])
    db.session.commit()
    return redirect(url_for('stock'))

@app.route('/stock/delete/<int:med_id>', methods=['POST'])
def delete_medicine(med_id):
    med = Medicine.query.get_or_404(med_id)
    db.session.delete(med)
    db.session.commit()
    return redirect(url_for('stock'))

@app.route('/api/ai-reorder', methods=['POST'])
def ai_reorder():
    low_stock = Medicine.query.filter(Medicine.quantity <= Medicine.reorder_level).all()
    if not low_stock:
        return jsonify({"message": "All medicines are well-stocked!", "items": []})
    items_text = "\n".join([f"- {m.name}: qty={m.quantity}, reorder_level={m.reorder_level}" for m in low_stock])
    prompt = f"""Pharmacy medicines running low:\n{items_text}\nReturn ONLY valid JSON array, no extra text:
[{{"name":"...","reorder_qty":50,"priority":"Critical/High/Medium","reason":"..."}}]"""
    text = ai(prompt)
    if "```" in text:
        text = text.split("```")[1].replace("json","").strip()
    try:
        suggestions = json.loads(text)
    except:
        return jsonify({"error": "AI response parsing failed", "items": []})
    return jsonify({"message": f"{len(low_stock)} items need reordering", "items": suggestions})

# ── APPOINTMENTS ───────────────────────────────────────────────
@app.route('/appointments')
def appointments():
    doctors   = Doctor.query.all()
    all_appts = Appointment.query.order_by(Appointment.appointment_date).all()
    return render_template('appointments.html', doctors=doctors, appointments=all_appts)

@app.route('/appointments/book', methods=['POST'])
def book_appointment():
    data = request.form
    existing = Appointment.query.filter_by(
        doctor_id=int(data['doctor_id']),
        appointment_date=data['appointment_date'],
        appointment_time=data['appointment_time']
    ).first()
    if existing:
        doctors   = Doctor.query.all()
        all_appts = Appointment.query.order_by(Appointment.appointment_date).all()
        return render_template('appointments.html', doctors=doctors, appointments=all_appts,
                               error="That slot is already booked. Please choose another time.")
    appt = Appointment(patient_name=data['patient_name'], patient_age=int(data['patient_age']),
                       symptoms=data['symptoms'], doctor_id=int(data['doctor_id']),
                       appointment_date=data['appointment_date'], appointment_time=data['appointment_time'])
    db.session.add(appt)
    db.session.commit()
    return redirect(url_for('appointments'))

@app.route('/appointments/delete/<int:appt_id>', methods=['POST'])
def delete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for('appointments'))

@app.route('/api/suggest-doctor', methods=['POST'])
def suggest_doctor():
    symptoms = request.json.get('symptoms', '')
    doctors  = Doctor.query.all()
    doc_list = "\n".join([f"- {d.name} ({d.specialty})" for d in doctors])
    prompt = f"""Patient symptoms: {symptoms}

Available doctors:
{doc_list}

Pick the best doctor. Return ONLY valid JSON, no extra text:
{{"doctor_name":"Dr. Full Name","specialty":"Specialty","reason":"brief reason","urgency":"Low/Medium/High"}}"""
    text = ai(prompt)
    if "```" in text:
        text = text.split("```")[1].replace("json","").strip()
    try:
        result = json.loads(text)
        result.setdefault("urgency",   "Medium")
        result.setdefault("specialty", "General Physician")
        result.setdefault("reason",    "Based on your symptoms")
    except:
        result = {"doctor_name":"Dr. Priya Sharma","specialty":"General Physician",
                  "reason":"General physician recommended for your symptoms","urgency":"Medium"}
    return jsonify(result)

# ── CHATBOT ────────────────────────────────────────────────────
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data         = request.json
    user_message = data.get('message', '')
    history      = data.get('history', [])
    if not user_message.strip():
        return jsonify({"reply": "Please enter a message."})
    medicines = Medicine.query.all()
    med_list  = ", ".join([f"{m.name} (qty:{m.quantity})" for m in medicines])
    messages  = [{"role": "system", "content": f"You are SmartClinic assistant. Medicines: {med_list}. Be helpful, concise, under 80 words."}]
    for msg in history[-6:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", messages=messages, max_tokens=300)
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"reply": "Something went wrong. Please try again."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)