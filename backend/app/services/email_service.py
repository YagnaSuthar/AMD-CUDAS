"""
Email service — sends verification, password-reset, and credential emails via Gmail SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Returns True on success."""
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        print(f"[EMAIL STUB] To: {to_email} | Subject: {subject}")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def send_verification_email(to_email: str, otp: str) -> bool:
    html = f"""
    <div style="font-family:'Inter', Arial, sans-serif; max-width:600px; margin:auto; padding:30px; background-color:#f8fafc; border-radius:12px; border:1px solid #e2e8f0;">
        <div style="text-align:center; margin-bottom:24px;">
            <h2 style="font-family:'Orbitron', sans-serif; color:#00bcd4; margin:0; font-size:24px;">CUDAS</h2>
            <p style="color:#64748b; font-size:14px; margin-top:4px;">Education Platform Security</p>
        </div>
        
        <div style="background:#ffffff; padding:32px; border-radius:8px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1); text-align:center;">
            <h3 style="color:#1e293b; margin-top:0;">Verify Your Email</h3>
            <p style="color:#475569; line-height:1.6; margin-bottom:24px;">
                Thank you for registering. Please use the following 6-digit One-Time Password (OTP) to verify your email address. This code will expire in 15 minutes.
            </p>
            
            <div style="letter-spacing:6px; font-size:32px; font-weight:bold; color:#00bcd4; background:#f0fdfa; padding:16px; border-radius:6px; display:inline-block; margin-bottom:24px; border:1px solid #ccfbf1;">
                {otp}
            </div>
            
            <p style="color:#94a3b8; font-size:13px; margin:0;">
                If you did not request this verification, please ignore this email.
            </p>
        </div>
    </div>
    """
    return _send_email(to_email, "CUDAS — Your Verification OTP", html)


def send_reset_password_email(to_email: str, token: str, base_url: str) -> bool:
    reset_url = f"{base_url}/reset-password?token={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
        <h2 style="color:#00bcd4;">CUDAS — Reset Your Password</h2>
        <p>Click the button below to reset your password:</p>
        <a href="{reset_url}"
           style="display:inline-block;padding:12px 32px;background:#00bcd4;color:#fff;
                  text-decoration:none;border-radius:6px;font-weight:bold;">
            Reset Password
        </a>
        <p style="color:#888;margin-top:20px;">This link expires in 1 hour.</p>
    </div>
    """
    return _send_email(to_email, "CUDAS — Reset Your Password", html)


def send_credentials_email(to_email: str, name: str, reset_token: str, role: str, base_url: str) -> bool:
    reset_url = f"{base_url}/reset-password?token={reset_token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;border:1px solid #eee;border-radius:10px;">
        <h2 style="color:#00bcd4;">CUDAS — Welcome to the Platform</h2>
        <p>Hello <strong>{name}</strong>,</p>
        <p>Your account has been created with the role <strong>{role}</strong>.</p>
        <p>To get started, please click the link below to set your password and activate your account:</p>
        <div style="text-align:center;margin:30px 0;">
            <a href="{reset_url}" 
               style="background:#00bcd4;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
                Set Your Password
            </a>
        </div>
        <p style="color:#666;font-size:12px;">If the button above doesn't work, copy and paste this link into your browser:</p>
        <p style="color:#00bcd4;font-size:12px;word-break:break-all;">{reset_url}</p>
        <p style="color:#888;margin-top:20px;font-size:13px;">This link is valid for 24 hours.</p>
    </div>
    """
    return _send_email(to_email, f"CUDAS — Welcome {name}! Set Your Password", html)
