"""
Email utility for sending password reset and fraud-alert emails.

Configuration via environment variables:
  SMTP_HOST     — SMTP server hostname (default: smtp.gmail.com)
  SMTP_PORT     — SMTP server port (default: 587)
  SMTP_USER     — SMTP login username / sender address
  SMTP_PASS     — SMTP login password or app password
  SMTP_FROM     — From address (defaults to SMTP_USER)
  APP_URL       — Frontend base URL (default: http://localhost:5173)

If SMTP_USER / SMTP_PASS are not set the reset link is printed to stdout
so the flow still works in development without an email provider.

PRODUCTION NOTE
---------------
Set the six variables above in the environment (e.g. backend/.env or your
deployment platform's secrets) before deploying.  The app logs a loud WARNING
at startup when credentials are absent so misconfiguration is never silent.
See docs/smtp-setup.md for a step-by-step guide.

Design note: all functions read config dynamically from os.environ at call
time (via _cfg()) rather than from module-level constants.  This makes unit
testing straightforward (patch os.environ, no module reload needed) and
ensures secrets set after process start (e.g. via dotenv) are always picked up.
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Required for real email delivery ──────────────────────────────────────────
_REQUIRED_FOR_SMTP = ["SMTP_USER", "SMTP_PASS"]


def _cfg() -> dict:
    """
    Read SMTP/app configuration fresh from os.environ on every call.

    Returns a dict with keys: smtp_host, smtp_port, smtp_user, smtp_pass,
    smtp_from, app_url.  Callers that need a key should use this helper so
    secrets set after process startup (e.g. via dotenv) are always picked up.
    """
    smtp_user = os.getenv("SMTP_USER", "")
    return {
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": smtp_user,
        "smtp_pass": os.getenv("SMTP_PASS", ""),
        "smtp_from": os.getenv("SMTP_FROM", smtp_user),
        "app_url":   os.getenv("APP_URL", "http://localhost:5173"),
    }


def check_email_config() -> dict:
    """
    Inspect the current SMTP configuration and return a status dict.

    Returns::

        {
            "configured": bool,   # True when all required vars are set
            "missing":    list,   # required vars that are absent
            "warnings":   list,   # optional vars that still have dev defaults
        }

    Call this at application startup (see main.py lifespan) so that a
    misconfigured production deployment fails visibly, not silently.
    """
    missing = [k for k in _REQUIRED_FOR_SMTP if not os.getenv(k)]
    warnings: list[str] = []

    if not missing:
        cfg = _cfg()
        if cfg["app_url"] == "http://localhost:5173":
            warnings.append(
                "APP_URL is not set — reset links will point to localhost, "
                "which won't work for real users.  Set APP_URL to your "
                "production frontend URL (e.g. https://secureai.example.com)."
            )
        if not os.getenv("SMTP_FROM"):
            warnings.append(
                "SMTP_FROM is not set — From address will default to SMTP_USER."
            )

    return {
        "configured": len(missing) == 0,
        "missing": missing,
        "warnings": warnings,
    }


def send_password_reset_email(to_email: str, token: str) -> None:
    """Send a password-reset email. Falls back to console logging in dev."""
    cfg = _cfg()
    reset_link = f"{cfg['app_url']}/reset-password?token={token}"

    if not cfg["smtp_user"] or not cfg["smtp_pass"]:
        # Development fallback — no SMTP credentials configured.
        logger.warning(
            "SMTP not configured. Password reset link for %s: %s",
            to_email,
            reset_link,
        )
        print(f"\n[DEV] Password reset link for {to_email}:\n  {reset_link}\n")
        return

    subject = "Reset your Alinma SecureAI password"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
  <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="text-align:center;margin-bottom:24px;">
      <span style="font-size:28px;">🔐</span>
      <h2 style="color:#0a1f3f;margin:8px 0 4px;">Alinma SecureAI</h2>
      <p style="color:#888;font-size:13px;margin:0;">AI-powered fraud prevention</p>
    </div>
    <h3 style="color:#0a1f3f;">Reset your password</h3>
    <p style="color:#444;font-size:14px;line-height:1.6;">
      We received a request to reset the password for your account.
      Click the button below to set a new password. This link expires in <strong>1 hour</strong>.
    </p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{reset_link}"
         style="background:#b87333;color:#fff;text-decoration:none;padding:12px 28px;
                border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">
        Reset Password
      </a>
    </div>
    <p style="color:#888;font-size:12px;line-height:1.6;">
      If you didn't request this, you can safely ignore this email — your password won't change.<br>
      The link will expire in 1 hour.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="color:#bbb;font-size:11px;text-align:center;">
      Alinma Bank · SecureAI Platform
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Reset your Alinma SecureAI password\n\n"
        f"Click the link below to set a new password (expires in 1 hour):\n"
        f"{reset_link}\n\n"
        f"If you did not request this, ignore this email."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["smtp_from"]
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.sendmail(cfg["smtp_from"], [to_email], msg.as_string())
        logger.info("Password reset email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
        raise


def send_fraud_alert_email(
    to_email: str,
    customer_name: str,
    alert_type: str,
    severity: str,
) -> None:
    """
    Send a fraud-alert notification email to the account holder.
    Falls back to console logging when SMTP credentials are not configured.
    """
    cfg = _cfg()
    login_link = f"{cfg['app_url']}/login"

    alert_type_label = alert_type.replace("_", " ").title()
    severity_upper = severity.upper()

    severity_color = {
        "HIGH": "#c0392b",
        "MEDIUM": "#e67e22",
        "LOW": "#2980b9",
    }.get(severity_upper, "#333")

    if not cfg["smtp_user"] or not cfg["smtp_pass"]:
        logger.warning(
            "SMTP not configured. Fraud alert notification for %s: type=%s severity=%s",
            to_email,
            alert_type,
            severity,
        )
        print(
            f"\n[DEV] Fraud alert email for {to_email} ({customer_name}): "
            f"type={alert_type_label}, severity={severity_upper}\n"
        )
        return

    subject = "⚠️ Fraud Alert Detected on Your Alinma Account"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
  <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="text-align:center;margin-bottom:24px;">
      <span style="font-size:28px;">🚨</span>
      <h2 style="color:#0a1f3f;margin:8px 0 4px;">Alinma SecureAI</h2>
      <p style="color:#888;font-size:13px;margin:0;">AI-powered fraud prevention</p>
    </div>
    <h3 style="color:#0a1f3f;">Fraud Alert on Your Account</h3>
    <p style="color:#444;font-size:14px;line-height:1.6;">
      Dear {customer_name},<br><br>
      Our system has detected a potential fraud event on your account.
      Please review the details below and log in to take action.
    </p>
    <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
      <tr style="background:#f9f9f9;">
        <td style="padding:10px 14px;color:#666;font-weight:600;border-radius:4px 0 0 4px;">Alert Type</td>
        <td style="padding:10px 14px;color:#333;">{alert_type_label}</td>
      </tr>
      <tr>
        <td style="padding:10px 14px;color:#666;font-weight:600;">Severity</td>
        <td style="padding:10px 14px;font-weight:700;color:{severity_color};">{severity_upper}</td>
      </tr>
    </table>
    <div style="text-align:center;margin:28px 0;">
      <a href="{login_link}"
         style="background:#b87333;color:#fff;text-decoration:none;padding:12px 28px;
                border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">
        Log In &amp; Review Alert
      </a>
    </div>
    <p style="color:#888;font-size:12px;line-height:1.6;">
      If you believe this alert is a mistake or did not initiate this activity,
      please contact Alinma Bank support immediately.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="color:#bbb;font-size:11px;text-align:center;">
      Alinma Bank · SecureAI Platform
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Fraud Alert on Your Alinma Account\n\n"
        f"Dear {customer_name},\n\n"
        f"Our system has detected a potential fraud event on your account.\n\n"
        f"Alert Type : {alert_type_label}\n"
        f"Severity   : {severity_upper}\n\n"
        f"Please log in and review this alert:\n{login_link}\n\n"
        f"If you did not initiate this activity, contact Alinma Bank support immediately."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["smtp_from"]
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.sendmail(cfg["smtp_from"], [to_email], msg.as_string())
        logger.info("Fraud alert email sent to %s (type=%s)", to_email, alert_type)
    except Exception as exc:
        logger.error("Failed to send fraud alert email to %s: %s", to_email, exc)
        raise
