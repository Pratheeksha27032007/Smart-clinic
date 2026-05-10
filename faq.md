# SmartClinic — FAQ & Troubleshooting

## ❓ Frequently Asked Questions

### Installation & Setup

**Q: I get "ModuleNotFoundError: No module named 'flask'"**
A: Install dependencies first:
```bash
pip install -r requirements_enhanced.txt
```

**Q: Database file not found**
A: The database is created automatically when you first run the app. If issues persist:
```bash
python
>>> from app_enhanced import app, db
>>> with app.app_context():
...     db.create_all()
```

**Q: .env file not being read**
A: Ensure python-dotenv is installed:
```bash
pip install python-dotenv
```

### Login & Authentication

**Q: I can't login with demo credentials**
A:
1. Make sure database was seeded properly (run app once)
2. Try exact credentials from SETUP_GUIDE.md
3. Check that FLASK_ENV is 'development' (not production)
4. Clear browser cache/cookies

**Q: Password must contain special character (!@#$%^&*)**
A: Update your password. Weak passwords are rejected for security:
- ✅ SecurePass123!
- ✅ MyClinic@2024
- ❌ password123 (no special char)
- ❌ Pass123 (too short)

**Q: "Invalid credentials or wrong role selected"**
A:
1. Make sure you select the correct role (Doctor, Pharmacy, Admin, or Patient)
2. Use exact email address (case-sensitive)
3. Verify password hasn't been changed

### Database Issues

**Q: "Database is locked" error**
A:
1. Check if another process is using the database
2. Close all Python shells that might have the database open
3. Delete smartclinic.db and restart (will reseed data)

**Q: I want to use PostgreSQL instead of SQLite**
A:
1. Install PostgreSQL: https://www.postgresql.org/download/
2. Create database: `createdb smartclinic_db`
3. Update .env: `DATABASE_URL=postgresql://user:password@localhost/smartclinic_db`
4. Install: `pip install psycopg2-binary`
5. Restart app

**Q: How do I backup the database?**
A:
```bash
# SQLite
cp smartclinic.db smartclinic_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump smartclinic_db > backup_$(date +%Y%m%d).sql
```

### Features & Functionality

**Q: Can I book an appointment in the past?**
A: No, by design. Dates are validated to be in the future (1-90 days out).

**Q: Why can't I double-book the same doctor at the same time?**
A: The system prevents scheduling conflicts. Each doctor can only have one appointment per time slot.

**Q: Can patients see other patients' information?**
A: No. The app enforces role-based access control. Patients can only see their own data.

**Q: How do prescriptions work?**
A:
1. Doctor creates prescription after appointment
2. Prescription gets sent to pharmacy
3. Patient views prescription in dashboard
4. Patient can place order based on prescription
5. Pharmacy fulfills order

### AI & API Features

**Q: AI suggestions not working**
A:
1. Verify GROQ_API_KEY is set in .env
2. Check internet connection
3. Verify Groq API account is active and has credits
4. Check error logs for detailed message

**Q: "AI service temporarily unavailable"**
A: The Groq API might be down or rate-limited. Try again in a few moments.

**Q: Can I use a different AI provider?**
A: Yes! Modify the `ai()` function in app_enhanced.py to use OpenAI, Claude, etc.

### Email & Notifications

**Q: Emails not sending**
A:
1. Enable 2FA on Gmail account
2. Create app-specific password: https://myaccount.google.com/apppasswords
3. Update .env with app password (not main password)
4. Check MAIL_DEFAULT_SENDER is set
5. Verify MAIL_USERNAME matches

**Q: "Connection refused" on email**
A:
1. Check firewall (port 587)
2. Try port 465 (SSL instead of TLS)
3. Verify MAIL_SERVER address

### Deployment Issues

**Q: App won't start on Render/Heroku**
A:
1. Check build logs: `heroku logs --tail`
2. Verify all required environment variables are set
3. Check Python version compatibility (3.8+)
4. Run `heroku config` to see all env vars

**Q: Database errors after deployment**
A:
1. Set DATABASE_URL to production PostgreSQL
2. Run migrations: `flask db upgrade`
3. Verify user has database creation permissions

**Q: "SECRET_KEY missing" error**
A: Set in deployment platform:
```bash
heroku config:set SECRET_KEY="your-very-long-random-string"
```

### Performance & Optimization

**Q: App is slow**
A:
1. Check database size: `ls -lh smartclinic.db`
2. Clean old orders/messages: `DELETE FROM message WHERE created_at < date('now', '-90 days')`
3. Add database indexes for frequently queried fields
4. Switch to PostgreSQL for better performance
5. Enable caching

**Q: Too many API requests**
A:
1. Enable rate limiting in config.py
2. Implement caching for doctor/medicine lists
3. Optimize AI API calls (cache results when possible)

### Security Concerns

**Q: Is my data safe?**
A: We implement:
- ✅ Password hashing (werkzeug)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ CSRF protection ready
- ✅ Session security (HTTPOnly, SameSite)
- ✅ Input validation
- ✅ Audit logging

Still recommended:
- Use HTTPS in production
- Regular database backups
- Strong SECRET_KEY in .env
- Monitor logs for suspicious activity

**Q: How do I reset a user password?**
A:
```python
# Admin command
python
>>> from app_enhanced import app, db
>>> from database import User
>>> with app.app_context():
...     user = User.query.filter_by(email="patient@example.com").first()
...     user.set_password("NewPassword123!")
...     db.session.commit()
...     print("Password reset successful")
```

**Q: Can I export patient data?**
A: Not yet, but can be implemented. Use your database tool to export CSV/SQL.

---

## 🔧 Troubleshooting Checklist

When something goes wrong, try these steps:

- [ ] Check error message carefully (often tells you what's wrong)
- [ ] Look at logs: `tail -f smartclinic.log`
- [ ] Verify .env file exists and has required keys
- [ ] Restart the application
- [ ] Clear browser cache (Ctrl+Shift+Delete)
- [ ] Check internet connection
- [ ] Try in different browser
- [ ] Test with demo credentials first
- [ ] Check Python version: `python --version` (need 3.8+)
- [ ] Verify no other app is using port 5000

---

## 🆘 Getting Help

1. **Check Logs**: `cat smartclinic.log`
2. **Read Documentation**: See SETUP_GUIDE.md
3. **Search GitHub Issues**: https://github.com/yourrepo/issues
4. **Contact Support**: support@smartclinic.com
5. **Stack Overflow**: Tag with [flask], [sqlalchemy], [sqlite]

---

## 📋 Common Error Messages & Solutions

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: flask` | `pip install -r requirements_enhanced.txt` |
| `sqlalchemy.exc.OperationalError: database is locked` | Restart app, close other connections |
| `GROQ_API_KEY not found` | Add to .env file, restart app |
| `Password must be at least 8 characters` | Use stronger password: `SecurePass123!` |
| `Invalid email format` | Use valid email: `user@example.com` |
| `Appointment date must be in future` | Can't book in the past |
| `SMTP Connection refused` | Check MAIL_SERVER, port, and firewall |
| `secret key not provided` | Set SECRET_KEY in .env |
| `404 Not Found` | Check route name and HTTP method (GET/POST) |

---

## 🐛 Report a Bug

Found a bug? Help us improve:

1. Check if already reported in Issues
2. Provide:
   - Python version
   - Error message (full traceback)
   - Steps to reproduce
   - Expected vs actual behavior
3. Share sanitized error logs

---

**Last Updated**: January 2025 | v2.0

*Have a question not listed here? Create an issue on GitHub!*