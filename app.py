# app.py
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from threading import Thread

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super-secret-key')

# Hardcoded login
HARD_USERNAME = 'Pradeep Rajput'
HARD_PASSWORD = 'Pappu@882'

# Login decorator
def require_login(f):
    def wrapper(*args, **kwargs):
        if 'user' in session and session['user'] == HARD_USERNAME:
            return f(*args, **kwargs)
        return redirect('/login')
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == HARD_USERNAME and password == HARD_PASSWORD:
            session['user'] = username
            return redirect('/')
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/', methods=['GET'])
@require_login
def index():
    return render_template('form.html', message=None, bulk_count=0, formData={})

# Mail sending function (background thread)
def send_emails(snapshot):
    sender_email = snapshot['sender_email']
    sender_pass = snapshot['sender_pass']
    subject = snapshot['subject']
    body = snapshot['body']
    first_name = snapshot['first_name']
    recipients = snapshot['recipients']

    for to_email in recipients:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject or '(No Subject)'
            msg['From'] = f"{first_name or sender_email} <{sender_email}>"
            msg['To'] = to_email

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_pass)
                server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Sent to {to_email}")
        except Exception as e:
            print(f"Failed to send to {to_email}: {str(e)}")

@app.route('/send', methods=['POST'])
@require_login
def send():
    first_name = request.form.get('firstName')
    sender_email = request.form.get('sentFrom')
    sender_pass = request.form.get('appPassword')
    subject = request.form.get('subject')
    body = request.form.get('body')
    bulkMails = request.form.get('bulkMails', '')

    recipients = [email.strip() for email in bulkMails.splitlines() if email.strip()]
    bulk_count = len(recipients)

    snapshot = {
        'first_name': first_name,
        'sender_email': sender_email,
        'sender_pass': sender_pass,
        'subject': subject,
        'body': body,
        'recipients': recipients
    }

    # Start background thread
    Thread(target=send_emails, args=(snapshot,), daemon=True).start()

    message = f"Started sending {bulk_count} emails in background!"
    return render_template('form.html', message=message, bulk_count=bulk_count, formData=request.form)

if __name__ == '__main__':
    app.run(debug=True)
