from flask import Flask, render_template, request, redirect, session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = 'bulk-mailer-secret-please-change'

HARD_USERNAME = 'Pradeep Rajput'
HARD_PASSWORD = 'Pappu@882'

EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
MAX_PER_BATCH = 30
PORT = int(os.environ.get("PORT", 5000))

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
    session.pop('user', None)
    return redirect('/login')

# Login required decorator
def require_login(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Main form
@app.route('/', methods=['GET'])
@require_login
def index():
    return render_template('form.html', message=None, count=0, formData={}, bulk_count=0)

# Function to send single email
def send_single_email(server, snapshot, to_email):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{snapshot['firstName'] or snapshot['senderEmail']} <{snapshot['senderEmail']}>"
        msg['To'] = to_email
        msg['Subject'] = snapshot['subject']
        msg.attach(MIMEText(snapshot['body'], 'plain'))
        server.sendmail(snapshot['senderEmail'], to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed {to_email}: {e}")
        return False

# Send mails
@app.route('/send', methods=['POST'])
@require_login
def send():
    firstName = request.form.get('firstName')
    senderEmail = request.form.get('sentFrom')
    senderAppPassword = request.form.get('appPassword')
    subject = request.form.get('subject') or "(No subject)"
    body = request.form.get('body') or ""
    bulkMails = request.form.get('bulkMails') or ""

    if not senderEmail or not senderAppPassword:
        return render_template('form.html', message='Sender email and app password required.',
                               count=0, formData=request.form, bulk_count=0)

    # Parse recipients
    recipients = [r.strip() for r in re.split(r'[\n,;]+', bulkMails) if r.strip()]
    recipients = list(dict.fromkeys(recipients))  # remove duplicates
    limitedRecipients = recipients[:MAX_PER_BATCH]

    validRecipients = [r for r in limitedRecipients if EMAIL_REGEX.match(r)]
    invalidRecipients = [r for r in limitedRecipients if not EMAIL_REGEX.match(r)]

    # Snapshot to prevent overwrite during sending
    snapshot = {
        'firstName': firstName,
        'senderEmail': senderEmail,
        'senderAppPassword': senderAppPassword,
        'subject': subject,
        'body': body,
        'recipients': list(validRecipients)
    }

    sentCount = 0
    try:
        # Single SMTP connection for batch sending
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(snapshot['senderEmail'], snapshot['senderAppPassword'])

            # Thread pool for parallel sending
            with ThreadPoolExecutor(max_workers=5) as executor:  # 5 mails parallel
                results = list(executor.map(lambda to: send_single_email(server, snapshot, to), snapshot['recipients']))

            sentCount = sum(results)

        # Calculate bulk count safely
        bulk_count = len(validRecipients)

        msg_text = f"Successfully sent {sentCount} emails."
        if invalidRecipients:
            msg_text += f" Skipped {len(invalidRecipients)} invalid addresses."

        return render_template('form.html', message=msg_text, count=len(recipients), formData=request.form, bulk_count=bulk_count)

    except Exception as e:
        print('Send error:', e)
        bulk_count = len(re.findall(r'[^\s,;]+', bulkMails or ''))
        return render_template('form.html', message=f"Error sending: {e}", count=len(recipients), formData=request.form, bulk_count=bulk_count)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
