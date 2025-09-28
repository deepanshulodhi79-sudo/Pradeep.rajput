import os
from celery import Celery
from smtplib import SMTP_SSL
from email.mime.text import MIMEText

celery = Celery('tasks', broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

@celery.task
def send_bulk_emails_task(firstName, senderEmail, senderAppPassword, subject, body, recipients):
    import time
    from concurrent.futures import ThreadPoolExecutor

    MAX_WORKERS = 5

    def send_email(to_email):
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject or '(No Subject)'
            msg['From'] = f"{firstName or senderEmail} <{senderEmail}>"
            msg['To'] = to_email

            with SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(senderEmail, senderAppPassword)
                server.sendmail(senderEmail, [to_email], msg.as_string())
            return to_email
        except Exception as e:
            print(f"Failed to send to {to_email}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(send_email, recipients))

    print(f"Sent {len([r for r in results if r])}/{len(recipients)} emails successfully")
