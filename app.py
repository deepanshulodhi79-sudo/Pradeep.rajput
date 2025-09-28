import os
from flask import Flask, render_template, request, redirect, session
from tasks import send_bulk_emails_task
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super-secret')

# Hardcoded login
HARD_USERNAME = 'Yatendra Rajput'
HARD_PASSWORD = 'Yattu@882'

def require_login(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('user') == HARD_USERNAME:
            return f(*args, **kwargs)
        return redirect('/login')
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

@app.route('/')
@require_login
def index():
    return render_template('form.html', message=None, count=0, bulk_count=0, formData={})

@app.route('/send', methods=['POST'])
@require_login
def send():
    firstName = request.form.get('firstName', '')
    sentFrom = request.form.get('sentFrom', '')
    appPassword = request.form.get('appPassword', '')
    subject = request.form.get('subject', '')
    body = request.form.get('body', '')
    bulkMails = request.form.get('bulkMails', '')

    recipients = [r.strip() for r in bulkMails.replace(',', '\n').split('\n') if r.strip()]
    bulk_count = len(recipients)

    if not sentFrom or not appPassword:
        return render_template('form.html', message="Sender email & app password required",
                               count=0, bulk_count=bulk_count, formData=request.form)

    # Trigger Celery background task
    send_bulk_emails_task.delay(firstName, sentFrom, appPassword, subject, body, recipients)

    return render_template('form.html', message=f"Mail sending started in background for {bulk_count} recipients",
                           count=bulk_count, bulk_count=bulk_count, formData=request.form)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
