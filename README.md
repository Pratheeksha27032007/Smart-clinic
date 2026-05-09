# SmartClinic 🏥 — AI-Powered Healthcare Management System

A modern, full-stack web application for managing clinics, pharmacies, and patient care with AI-powered features.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.0-green)

---

## ✨ Features

### 🩺 **For Patients**
- 📅 Book appointments with AI doctor suggestions based on symptoms
- 👤 Comprehensive health profiles with allergy tracking
- 💊 Order medicines with real-time tracking
- 📝 Receive digital prescriptions
- 💬 Message doctors directly
- 📊 Medical history and profile management

### 👨‍⚕️ **For Doctors**
- 📋 Manage appointments (accept/decline/complete)
- 💊 Create digital prescriptions
- 👥 Access patient medical histories
- 📝 Add clinical notes
- 💬 Patient communication

### 🏥 **For Pharmacy**
- 📦 Manage medicine inventory with AI reorder suggestions
- 📥 Process orders (accept → pack → ship → deliver)
- 💳 Handle billing and payments
- 📊 Stock alerts and low inventory warnings

### 🏢 **For Hospital/Admin**
- 👨‍⚕️ Doctor management and scheduling
- 📊 Financial analytics and revenue tracking
- 🚚 Shipment tracking
- 📈 Hospital dashboard and reporting

### 🤖 **AI Features**
- Smart doctor recommendations based on symptoms
- Intelligent medicine reorder suggestions
- AI-powered chatbot for 24/7 support

---

## 🏗️ Architecture

```
Frontend (Jinja2 Templates)
        ↓
Flask Application (app_enhanced.py)
        ↓
SQLAlchemy ORM (database.py)
        ↓
SQLite/PostgreSQL Database
        ↓
External APIs (Groq AI, Razorpay, Twilio)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip / virtualenv
- Git

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/smartclinic.git
cd smartclinic
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements_enhanced.txt
```

4. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize Database**
```bash
python
>>> from app_enhanced import app, db
>>> with app.app_context():
...     db.create_all()
...     exit()
```

6. **Run Application**
```bash
python app_enhanced.py
# Visit http://localhost:5000
```

---

## 👥 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Doctor | doctor@smartclinic.com | Doctor@123 |
| Pharmacy | pharmacy@smartclinic.com | Pharma@123 |
| Admin | admin@smartclinic.com | Admin@123 |

---

## 📁 Project Structure

```
smartclinic/
├── app_enhanced.py                 # Main Flask application
├── database.py                     # Database models
├── config.py                       # Configuration management
├── requirements_enhanced.txt        # Dependencies
├── .env.example                    # Environment template
├── SETUP_GUIDE.md                 # Detailed setup instructions
│
├── templates/
│   ├── base.html                  # Base template
│   ├── login.html                 # Login page
│   ├── register.html              # Patient registration
│   ├── index.html                 # Role-based dashboard
│   ├── patient_profile.html       # Patient health profile
│   ├── patient_appointments.html  # Book appointments
│   ├── patient_medicines.html     # Order medicines
│   ├── patient_orders.html        # Track orders
│   ├── doctor_appointments.html   # Doctor appointments
│   ├── doctor_prescriptions.html  # Create prescriptions
│   ├── pharmacy_stock.html        # Inventory management
│   ├── pharmacy_orders.html       # Order processing
│   ├── mgmt_doctors.html          # Doctor management
│   ├── mgmt_orders.html           # Shipment tracking
│   ├── mgmt_funding.html          # Financial analytics
│   ├── messages.html              # Messaging system
│   └── chatbot.html               # AI chatbot
│
├── static/
│   ├── style.css                  # Main stylesheet
│   ├── script.js                  # Client-side logic
│   └── images/
│
└── uploads/                        # User-uploaded files
```

---

## 🔐 Security Features

✅ **Strong Password Requirements**
- Minimum 8 characters
- Uppercase letter required
- Number required
- Special character required (!@#$%^&*)

✅ **Input Validation**
- Email format validation
- Phone number validation
- Date range checking
- XSS prevention

✅ **Session Security**
- HTTPOnly cookies
- SameSite protection
- Secure flag in production
- Session timeout

✅ **Database Security**
- SQL injection prevention via ORM
- Parameterized queries
- Password hashing (werkzeug)

✅ **Audit Logging**
- Activity tracking
- Login/logout logs
- Action timestamps
- IP address logging

---

## 🌐 Deployment

### Render.com (Recommended)
```bash
git push origin main
# Auto-deploys from GitHub
```

### Heroku
```bash
heroku create smartclinic
git push heroku main
heroku config:set FLASK_ENV=production
```

### Docker
```bash
docker build -t smartclinic .
docker run -p 5000:5000 smartclinic
```

---

## 🔗 API Endpoints

### Authentication
```
POST   /login              Login user
POST   /register           Register patient
GET    /logout             Logout
```

### Patient Routes
```
GET    /patient/profile                     View health profile
POST   /patient/profile                     Update profile
GET    /patient/appointments                View appointments
POST   /patient/book                        Book appointment
POST   /patient/medicines                   Browse medicines
POST   /patient/order                       Place medicine order
GET    /patient/orders                      Track orders
```

### Doctor Routes
```
GET    /doctor/appointments                 View appointments
POST   /doctor/accept/<id>                  Accept appointment
POST   /doctor/decline/<id>                 Decline appointment
GET    /doctor/prescriptions                View prescriptions
POST   /doctor/prescriptions                Create prescription
POST   /doctor/set-schedule                 Set availability
```

### Pharmacy Routes
```
GET    /pharmacy/stock                      Manage inventory
POST   /pharmacy/stock/add                  Add medicine
POST   /pharmacy/stock/update/<id>          Update quantity
POST   /pharmacy/orders                     View orders
POST   /pharmacy/accept-order/<id>          Accept order
POST   /pharmacy/pack-order/<id>            Pack order
POST   /pharmacy/ship-order/<id>            Ship order
```

### AI APIs
```
POST   /api/suggest-doctor                  AI doctor suggestion
POST   /api/chat                            Chatbot
POST   /api/ai-reorder                      Reorder suggestions
```

---

## 📦 Dependencies

**Core**
- Flask 3.0.0
- Flask-SQLAlchemy 3.1.1
- Werkzeug 3.0.1
- Gunicorn 21.2.0

**AI & APIs**
- Groq 0.4.2
- Requests 2.31.0

**Security & Configuration**
- Python-dotenv 1.0.0
- Cryptography 41.0.7

**Optional (Enhanced Features)**
- Flask-Mail 0.9.1 (Email notifications)
- Flask-Limiter 3.5.0 (Rate limiting)
- Sentry-SDK 1.38.0 (Error tracking)
- Alembic 1.13.1 (Database migrations)

---

## 🧪 Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test
python -m pytest tests/test_auth.py
```

---

## 🐛 Known Issues

- [ ] SMS integration pending Twilio setup
- [ ] Payment gateway requires Razorpay account
- [ ] Email notifications need SMTP configuration
- [ ] Real-time updates require WebSocket implementation

---

## 🚧 Roadmap

**v2.1** (Next Release)
- [ ] Email appointment reminders
- [ ] SMS notifications
- [ ] Payment gateway integration
- [ ] Real-time order updates

**v2.2**
- [ ] Analytics dashboard
- [ ] Doctor availability calendar
- [ ] Drug interaction warnings
- [ ] Insurance integration

**v3.0**
- [ ] Mobile app (React Native)
- [ ] Telemedicine (video calls)
- [ ] Machine learning diagnostics
- [ ] Multi-language support

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📞 Support

- **Issues**: GitHub Issues
- **Email**: support@smartclinic.com
- **Documentation**: See `SETUP_GUIDE.md`

---

## 📄 License

This project is licensed under the MIT License — see LICENSE file for details.

---

## 👏 Acknowledgments

- Groq AI for LLM capabilities
- Flask community
- SQLAlchemy team
- All contributors

---

## 📊 Statistics

- **Lines of Code**: 2000+
- **Database Tables**: 8
- **API Endpoints**: 25+
- **User Roles**: 4
- **Features**: 40+

---

**Built with ❤️ for healthcare professionals**

*Last Updated: January 2025 | v2.0*
