import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_email_alert(subject, body, recipient=None):
    """
    Sends email using Mailtrap SMTP (or any custom SMTP relay).
    Falls back to simulation if credentials are missing.
    """
    # Load from .env (Adjusted variable names to match what is currently in your .env)
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("EMAIL_SENDER", "risk-monitor@demo.com")
    username = os.getenv("SMTP_USER", "")  
    password = os.getenv("SMTP_PASSWORD", "")
    recipient = recipient or os.getenv("ALERT_EMAIL", "neelkharva@crackone.org")

    # SIMULATION MODE: If no username/password, just log
    if not username or not password or password == "your_mailtrap_password":
        print(f"[SIMULATED EMAIL] To: {recipient} | Subject: {subject}")
        with open("email_log.txt", "a") as f:
            f.write(f"{subject} | {body}\n")
        return True

    # REAL MODE: Use Mailtrap or custom SMTP
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        if smtp_port == 587:
            server.starttls()
        server.login(username, password)
        server.send_message(message)
        server.quit()
        print(f"REAL EMAIL SENT via {smtp_host} to {recipient}")
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        # Fallback to simulation if real fails
        print(f"[FALLBACK SIMULATED] To: {recipient} | Subject: {subject}")
        with open("email_log.txt", "a") as f:
            f.write(f"{subject} | {body}\n")
        return False
