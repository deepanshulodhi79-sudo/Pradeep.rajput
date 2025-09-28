import os
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
import threading

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

HARD_USERNAME = "Pradeep Rajput"
HARD_PASSWORD = "Pappu@8822"

def require_login(f):
    def wrapper(*args, **kwargs):
        if session.get("user") == HARD_USERNAME:
            return f(*args, **kwargs)
        return redirect("/login")
    wrapper.__name__ = f.__name__
    return wrapper

@app.route("/login", methods=["GET","POST"])
def login():
    error=None
    if request.method=="POST":
        u=request.form.get("username")
        p=request.form.get("password")
        if u==HARD_USERNAME and p==HARD_PASSWORD:
            session["user"]=u
            return redirect("/")
        else:
            error="Invalid credentials"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/", methods=["GET"])
@require_login
def index():
    return render_template("form.html", message=None, count=0, bulk_count=0, formData={})

def send_email(sender_email, sender_pass, to_email, subject, body, sender_name):
    try:
        msg = EmailMessage()
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject or "(No subject)"
        msg.set_content(body or "")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_pass)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send to {to_email}: {e}")
        return False

def send_bulk_emails(snapshot):
    for to in snapshot["recipients"]:
        send_email(
            snapshot["sender_email"],
            snapshot["sender_pass"],
            to,
            snapshot["subject"],
            snapshot["body"],
            snapshot["first_name"]
        )

@app.route("/send", methods=["POST"])
@require_login
def send():
    first_name = request.form.get("firstName","")
    sender_email = request.form.get("sentFrom","").strip() or os.getenv("SENDER_EMAIL")
    sender_pass = request.form.get("appPassword","").strip() or os.getenv("SENDER_APP_PASSWORD")
    subject = request.form.get("subject","")
    body = request.form.get("body","")
    bulkMails = request.form.get("bulkMails","")

    recipients = [r.strip() for r in bulkMails.replace(',','\n').splitlines() if r.strip()]
    recipients = list(dict.fromkeys(recipients))  # remove duplicates
    bulk_count = len(recipients)

    if not sender_email or not sender_pass:
        return render_template("form.html", message="Sender email or password missing.", count=0, bulk_count=bulk_count, formData=request.form)

    snapshot = {
        "first_name": first_name,
        "sender_email": sender_email,
        "sender_pass": sender_pass,
        "subject": subject,
        "body": body,
        "recipients": recipients
    }

    # Threading for faster response
    threading.Thread(target=send_bulk_emails, args=(snapshot,)).start()

    return render_template("form.html", message=f"Started sending {bulk_count} emails in background!", count=bulk_count, bulk_count=bulk_count, formData=request.form)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)), debug=True)
