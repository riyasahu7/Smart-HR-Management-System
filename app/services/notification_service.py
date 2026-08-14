"""
Email Notification Service — Feature 2
Sends emails for: leave status, payslips, birthdays, work anniversaries.
"""
from datetime import datetime
from threading import Thread
from flask import current_app, render_template_string
from flask_mail import Message
from app import mail, mongo
from app.models.employee_model import EmployeeModel
from app.models.notification_model import NotificationModel


# ── In-App Notification Helpers ───────────────────────────────────────────────

def _notif_col():
    return mongo.db[NotificationModel.COLLECTION]


def _emp_col():
    return mongo.db[EmployeeModel.COLLECTION]


def create_notification(recipient_id, title, message, notif_type="general", link=None):
    """Store an in-app notification."""
    doc = NotificationModel.new(recipient_id, title, message, notif_type, link)
    _notif_col().insert_one(doc)


def get_notifications(user_id, unread_only=False, limit=20):
    query = {"recipient_id": user_id}
    if unread_only:
        query["is_read"] = False
    docs = list(
        _notif_col()
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    return [NotificationModel.to_dict(d) for d in docs]


def mark_read(notification_id, user_id):
    from bson import ObjectId
    _notif_col().update_one(
        {"_id": ObjectId(notification_id), "recipient_id": user_id},
        {"$set": {"is_read": True}}
    )


def mark_all_read(user_id):
    _notif_col().update_many(
        {"recipient_id": user_id},
        {"$set": {"is_read": True}}
    )


def unread_count(user_id):
    return _notif_col().count_documents({"recipient_id": user_id, "is_read": False})


# ── Email Sending (async so it doesn't block requests) ────────────────────────

def _send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"[Email Error] {e}")


def send_email(to, subject, html_body, cc=None):
    """Send email in a background thread."""
    app = current_app._get_current_object()
    sender = app.config.get("MAIL_USERNAME") or "noreply@smarthr.com"
    if not sender:
        return  # Mail not configured

    msg = Message(subject, sender=sender, recipients=[to] if isinstance(to, str) else to)
    if cc:
        msg.cc = cc if isinstance(cc, list) else [cc]
    msg.html = html_body
    Thread(target=_send_async_email, args=(app, msg)).start()


# ── Email Templates ───────────────────────────────────────────────────────────

_BASE_EMAIL = """
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#f8fafc;padding:20px;border-radius:8px">
  <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);padding:20px 24px;border-radius:8px 8px 0 0">
    <h1 style="color:#fff;margin:0;font-size:20px">🏢 Smart HR Management</h1>
  </div>
  <div style="background:#fff;padding:24px;border-radius:0 0 8px 8px;border:1px solid #e2e8f0">
    {body}
  </div>
  <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:12px">
    This is an automated email from Smart HR Management System.
  </p>
</div>
"""


def _render(body):
    return _BASE_EMAIL.replace("{body}", body)


# ── Feature Emails ────────────────────────────────────────────────────────────

def _app_url():
    """Return the base URL dynamically — works for both local and Vercel."""
    import os
    vercel_url = os.environ.get("VERCEL_URL")  # auto-set by Vercel e.g. smart-hr.vercel.app
    if vercel_url:
        return f"https://{vercel_url}"
    return os.environ.get("APP_URL", "http://localhost:5000")


def notify_leave_status(employee_email, employee_name, leave_type,
                        start_date, end_date, days, status, comments=""):
    color = "#10b981" if status == "approved" else "#ef4444"
    icon  = "✅" if status == "approved" else "❌"
    portal_url = _app_url()
    body = f"""
        <h2 style="color:{color}">{icon} Leave Request {status.title()}</h2>
        <p>Hi <strong>{employee_name}</strong>,</p>
        <p>Your leave request has been <strong style="color:{color}">{status}</strong>.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#f8fafc"><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>Leave Type</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0">{leave_type.title()}</td></tr>
          <tr><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>From</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0">{start_date}</td></tr>
          <tr style="background:#f8fafc"><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>To</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0">{end_date}</td></tr>
          <tr><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>Days</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0">{days}</td></tr>
          {"<tr style='background:#f8fafc'><td style='padding:8px 12px;border:1px solid #e2e8f0'><b>Remarks</b></td><td style='padding:8px 12px;border:1px solid #e2e8f0'>" + comments + "</td></tr>" if comments else ""}
        </table>
        <a href="{portal_url}/leave" style="background:#3b82f6;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;margin-top:8px">View Leave Portal</a>
    """
    send_email(employee_email, f"Leave Request {status.title()} — Smart HR", _render(body))


def notify_payslip(employee_email, employee_name, month, year,
                   gross, net, pay_period):
    portal_url = _app_url()
    body = f"""
        <h2 style="color:#3b82f6">💰 Payslip Available — {pay_period}</h2>
        <p>Hi <strong>{employee_name}</strong>,</p>
        <p>Your payslip for <strong>{pay_period}</strong> has been processed and is ready to view.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#f8fafc"><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>Pay Period</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0">{pay_period}</td></tr>
          <tr><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>Gross Salary</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0">Rs.{gross:,.2f}</td></tr>
          <tr style="background:#f8fafc"><td style="padding:8px 12px;border:1px solid #e2e8f0"><b>Net Payable</b></td><td style="padding:8px 12px;border:1px solid #e2e8f0;color:#10b981;font-weight:bold">Rs.{net:,.2f}</td></tr>
        </table>
        <a href="{portal_url}/payroll" style="background:#3b82f6;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;margin-top:8px">View Payslip</a>
    """
    send_email(employee_email, f"Payslip for {pay_period} — Smart HR", _render(body))


def notify_birthday(employee_email, employee_name):
    body = f"""
        <h2 style="color:#f59e0b">🎂 Happy Birthday, {employee_name}!</h2>
        <p>Wishing you a wonderful birthday filled with joy and happiness!</p>
        <p>The entire team at Smart HR wishes you a fantastic year ahead.</p>
        <p style="font-size:40px;text-align:center">🎉🎊🎈</p>
    """
    send_email(employee_email, f"Happy Birthday {employee_name}! 🎂 — Smart HR", _render(body))


def notify_work_anniversary(employee_email, employee_name, years):
    body = f"""
        <h2 style="color:#8b5cf6">🏆 Work Anniversary — {years} Year{'s' if years > 1 else ''}!</h2>
        <p>Hi <strong>{employee_name}</strong>,</p>
        <p>Congratulations on completing <strong>{years} year{'s' if years > 1 else ''}</strong> with us!</p>
        <p>Your dedication and hard work are truly valued. Thank you for being a vital part of our team.</p>
        <p style="font-size:40px;text-align:center">🌟⭐🏅</p>
    """
    send_email(employee_email, f"Work Anniversary — {years} Year(s)! 🏆 — Smart HR", _render(body))


def check_and_send_birthday_reminders():
    """Called by a scheduler or manually — checks today's birthdays and anniversaries."""
    today = datetime.utcnow()
    employees = list(_emp_col().find({"status": "active"}))
    sent = {"birthdays": 0, "anniversaries": 0}

    for emp in employees:
        dob = emp.get("date_of_birth")
        doj = emp.get("date_of_joining")
        email = emp.get("email")
        name = emp.get("full_name", "")

        if dob and email:
            if dob.month == today.month and dob.day == today.day:
                notify_birthday(email, name)
                sent["birthdays"] += 1

        if doj and email:
            if doj.month == today.month and doj.day == today.day:
                years = today.year - doj.year
                if years > 0:
                    notify_work_anniversary(email, name, years)
                    sent["anniversaries"] += 1

    return sent
