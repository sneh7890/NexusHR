import os
import random
import string
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.database import query, execute, execute_lastid

GMAIL_USER      = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", "")
OTP_EXPIRY_MINS = 10


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def create_otp(email, purpose):
    code       = generate_otp()
    expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=OTP_EXPIRY_MINS)).isoformat()
    execute("UPDATE otps SET used=1 WHERE email=? AND purpose=? AND used=0", (email.lower(), purpose))
    execute_lastid("INSERT INTO otps (email, otp_code, purpose, expires_at) VALUES (?,?,?,?)",
                   (email.lower(), code, purpose, expires_at))
    return code


def verify_otp(email, code, purpose):
    row = query(
        "SELECT * FROM otps WHERE email=? AND otp_code=? AND purpose=? AND used=0 "
        "ORDER BY created_at DESC LIMIT 1",
        (email.lower(), code, purpose), fetchone=True
    )
    if not row:
        return False, "Invalid OTP"
    expires_at = datetime.datetime.fromisoformat(row["expires_at"])
    if datetime.datetime.now() > expires_at:
        execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],))
        return False, "OTP has expired. Please request a new one."
    execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],))
    return True, "OK"


def send_email(to_email, subject, html_body, text_body=None):
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("WARNING: GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
        return False, "Email not configured"
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = "Nexus HR <{}>".format(GMAIL_USER)
        msg["To"]      = to_email
        msg["Subject"] = subject
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD in .env"
    except Exception as e:
        return False, str(e)


def _otp_html(title, message, otp_code, expiry_mins=10):
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0d0e12;font-family:Arial,sans-serif;">
  <div style="max-width:480px;margin:40px auto;background:#13151c;border:1px solid #272930;border-radius:16px;overflow:hidden;">
    <div style="background:linear-gradient(135deg,#f59e0b,#f97316);padding:28px 32px;">
      <h1 style="margin:0;color:#000;font-size:22px;font-weight:800;">Nexus HR</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#e2e8f0;font-size:20px;margin:0 0 12px;">{title}</h2>
      <p style="color:#94a3b8;font-size:15px;margin:0 0 28px;">{message}</p>
      <div style="background:#1e2028;border:2px dashed #f59e0b;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
        <div style="font-size:36px;font-weight:800;letter-spacing:10px;color:#f59e0b;font-family:monospace;">{otp}</div>
      </div>
      <p style="color:#64748b;font-size:13px;margin:0;">This code expires in <strong style="color:#94a3b8;">{expiry} minutes</strong>. Do not share it with anyone.</p>
    </div>
    <div style="padding:16px 32px;border-top:1px solid #272930;">
      <p style="color:#475569;font-size:12px;margin:0;">If you did not request this, please ignore this email.</p>
    </div>
  </div>
</body></html>""".format(title=title, message=message, otp=otp_code, expiry=expiry_mins)


def send_login_otp(email, full_name, otp_code):
    html = _otp_html("Login Verification",
                     "Hi {}! Use the code below to complete your login.".format(full_name), otp_code)
    return send_email(email, "Your Nexus HR Login OTP", html,
                      "Your OTP is: {}. Valid for {} minutes.".format(otp_code, OTP_EXPIRY_MINS))


def send_register_otp(email, full_name, otp_code):
    html = _otp_html("Verify Your Email",
                     "Hi {}! Enter the code below to verify your email.".format(full_name), otp_code)
    return send_email(email, "Verify Your Nexus HR Account", html,
                      "Your verification OTP is: {}. Valid for {} minutes.".format(otp_code, OTP_EXPIRY_MINS))


def send_forgot_otp(email, otp_code):
    html = _otp_html("Reset Your Password",
                     "We received a request to reset your Nexus HR password.",
                     otp_code)
    return send_email(email, "Nexus HR Password Reset", html,
                      "Your password reset OTP is: {}. Valid for {} minutes.".format(otp_code, OTP_EXPIRY_MINS))