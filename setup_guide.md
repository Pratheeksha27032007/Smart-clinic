# SmartClinic — Setup & Deployment Guide

## 🚀 Quick Start (Development)

### 1. **Clone & Install**
```bash
git clone <your-repo>
cd smartclinic
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements_enhanced.txt
```

### 2. **Set Up Environment Variables**
Create a `.env` file:
```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this

# Database
DATABASE_URL=sqlite:///smartclinic.db

# Groq AI
GROQ_API_KEY=your_groq_api_key

# Email (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password  # Use app-specific password
MAIL_DEFAULT_SENDER=smartclinic@example.com

# Payment Gateway (Razorpay - India)
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret

# SMS (Twilio - optional)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE=+1234567890
```

### 3. **Initialize Database**
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
...     exit()
```

### 4. **Run Development Server**
```bash
python app.py
# Visit http://localhost:5000
```

### 5. **Demo Credentials**
```
Doctor:   doctor@smartclinic.com / Doctor@123
Pharmacy: pharmacy@smartclinic.com / Pharma@123
Admin:    admin@smartclinic.com / Admin@123
```

---

## 📋 What's New in Enhanced Version

### ✅ Critical Additions
1. **Patient Health Profiles** — Allergies, conditions, emergency contact
2. **Prescription System** — Doctors create → Pharmacy dispenses → Patients use
3. **Input Validation** — Strong passwords, email format, phone validation
4. **Error Handling** — Proper try-catch, user feedback, logging
5. **Audit Logging** — Track all important actions

### ✅ Security Improvements
- Strong password requirements (8+ chars, uppercase, number, special char)
- SQL injection prevention via proper ORM
- CSRF protection ready
- Session security (HTTPOnly cookies, SameSite)
- Input validation on all forms
- Rate limiting setup (via Flask-Limiter)

### ✅ Better UX
- Real appointment slot validation
- Conflict prevention
- Proper error messages
- Activity logging for accountability

---

## 🔧 File Structure

```
smartclinic/
├── app_enhanced.py              # Main Flask app (use this)
├── database.py                  # Enhanced database models
├── config.py                    # Configuration management
├── requirements_enhanced.txt    # All dependencies
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── index.html
│   ├── patient_profile.html     # NEW
│   ├── doctor_prescriptions.html # NEW
│   └── ...other templates
│
├── static/
│   ├── style.css
│   ├── script.js
│   └── ...
│
├── .env                         # Environment variables (create this)
├── .gitignore
└── render.yaml                  # Deployment config
```

---

## 🚢 Deployment (Render/Heroku)

### Step 1: Update `render.yaml`
```yaml
services:
  - type: web
    name: smartclinic
    env: python
    buildCommand: pip install -r requirements_enhanced.txt
    startCommand: gunicorn app:app
    envVars:
      - key: FLASK_ENV
        value: production
      - key: SQLALCHEMY_DATABASE_URI
        value: postgresql://user:pass@host/dbname
      - key: SECRET_KEY
        scope: secret
      - key: GROQ_API_KEY
        scope: secret
```

### Step 2: Deploy to Render
```bash
git push origin main
# Render auto-deploys when you push
```

### Step 3: Set Up PostgreSQL (Production)
```bash
# On Render, add PostgreSQL database
# Copy connection string to SQLALCHEMY_DATABASE_URI
```

---

## 📚 Key Features by Role

### **Patient**
- ✅ Book appointments (with AI doctor suggestion)
- ✅ View medical profile (allergies, conditions)
- ✅ Order medicines
- ✅ Track orders
- ✅ Receive prescriptions
- ✅ Message doctors
- 🔜 Email appointment reminders
- 🔜 Payment integration

### **Doctor**
- ✅ View appointments
- ✅ Create prescriptions
- ✅ Message patients
- 🔜 Mark appointments complete
- 🔜 Add notes to patient profiles
- 🔜 View patient history

### **Pharmacy**
- ✅ Manage medicine stock
- ✅ Process orders (accept → pack → ship)
- ✅ AI reorder suggestions
- 🔜 Dispense prescriptions
- 🔜 Generate invoices

### **Hospital Admin**
- ✅ Manage doctors
- ✅ View shipments
- ✅ Track revenue
- 🔜 Analytics dashboard
- 🔜 Payment settlements

---

## 🔒 Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use strong, unique database password
- [ ] Enable HTTPS (SSL certificate)
- [ ] Set up email authentication (Gmail app password)
- [ ] Configure MAIL_DEFAULT_SENDER
- [ ] Enable rate limiting
- [ ] Set up error monitoring (Sentry)
- [ ] Regular database backups
- [ ] Review environment variables
- [ ] Test password validation rules

---

## 📊 API Endpoints (Key)

### Authentication
- `POST /login` — Login
- `POST /register` — Patient registration
- `GET /logout` — Logout

### Appointments
- `POST /patient/book` — Book appointment
- `GET /patient/appointments` — View appointments
- `POST /doctor/accept/<id>` — Accept appointment
- `POST /doctor/decline/<id>` — Decline appointment

### Prescriptions (NEW)
- `POST /doctor/prescriptions` — Create prescription
- `GET /doctor/prescriptions` — View prescriptions

### Medicines
- `GET /patient/medicines` — Browse medicines
- `POST /patient/order` — Place order
- `GET /patient/orders` — Track orders

### Messages
- `GET /messages` — View messages
- `POST /messages/send` — Send message

### AI
- `POST /api/suggest-doctor` — AI doctor suggestion
- `POST /api/chat` — Chat with AI
- `POST /api/ai-reorder` — AI reorder suggestions

---

## 🐛 Troubleshooting

### Database Issues
```bash
# Reset database (dev only)
rm smartclinic.db
python app.py  # Recreates with seeded data
```

### Email Not Sending
- Check MAIL_USERNAME and MAIL_PASSWORD
- For Gmail: Enable 2FA, create app-specific password
- Check firewall (port 587)

### Groq API Errors
- Verify GROQ_API_KEY is valid
- Check API rate limits (100 req/min)

### Password Validation Fails
- Needs: 8+ chars, 1 uppercase, 1 number, 1 special char (!@#$%^&*)
- Example: `SecurePass123!`

---

## 📈 Next Steps (Prioritized)

1. **Week 1**: Deploy MVP with validations
2. **Week 2**: Add email notifications + SMS
3. **Week 3**: Implement payment gateway
4. **Week 4**: Analytics dashboard
5. **Week 5**: Mobile app / PWA

---

## 🆘 Support

- Documentation: Check `templates/` for UI
- API Tests: Use Postman for testing
- Database: SQLite (dev) → PostgreSQL (prod)
- Logging: Check `smartclinic.log` for errors

---

## 📝 License

[Add your license here]

---

**Last Updated**: 2024 | Version 2.0
**Status**: Production-ready for MVP