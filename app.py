import os
import threading
from flask import Flask, render_template, request, session, redirect
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

# Load env variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'bulk-mailer-secret-please-change'

# Hardcoded login
HARD_USERNAME = 'Pradeep Rajput'
HARD_PASSWORD = 'Pappu@882'

# Login routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == HARD_USERNAME and password == HARD_PASSWORD:
            session['user'] = username
            return redirect('/')
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Login required decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('user') == HARD_USERNAME:
            return f(*args, **kwargs)
        return redirect('/login')
    return wrapper

# Main form
@app.route('/', methods=['GET'])
@login_required
def index():
    return render_template('form.html', message=None, count=0, bulk_count=0, formData={})

# Background mail sending function
def send_emails(snapshot):
    sender_email = snapshot['senderEmail']
    sender_password = snapshot['senderAppPassword']
    subject = snapshot['subject']
    body = snapshot['body']
    first_name = snapshot['firstName']
    recipients = snapshot['recipients']

    for to_email in recipients:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = f"{first_name or sender_email} <{sender_email}>"
            msg['To'] = to_email

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Sent to {to_email}")
        except Exception as e:
            print(f"Failed to send to {to_email}: {e}")

# Send route
@app.route('/send', methods=['POST'])
@login_required
def send():
    first_name = request.form.get('firstName')
    sender_email = request.form.get('sentFrom')
    sender_password = request.form.get('appPassword')
    subject = request.form.get('subject')
    body = request.form.get('body')
    bulk_mails = request.form.get('bulkMails', '')

    if not sender_email or not sender_password:
        return render_template('form.html', message='Sender email and password required.',
                               count=0, bulk_count=0, formData=request.form)

    recipients = [e.strip() for e in bulk_mails.replace(',', '\n').split('\n') if e.strip()]
    recipients = list(set(recipients))  # remove duplicates

    snapshot = {
        'firstName': first_name,
        'senderEmail': sender_email,
        'senderAppPassword': sender_password,
        'subject': subject,
        'body': body,
        'recipients': recipients
    }

    # Start background thread
    thread = threading.Thread(target=send_emails, args=(snapshot,))
    thread.start()

    return render_template('form.html',
                           message=f"Started sending {len(recipients)} emails in background.",
                           count=len(recipients),
                           bulk_count=len(recipients),
                           formData=request.form)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
