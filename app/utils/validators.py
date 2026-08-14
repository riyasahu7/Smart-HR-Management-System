"""
Request body validators.
"""
from app.utils.helpers import validate_email, validate_phone


def validate_employee_data(data, is_update=False):
    errors = []
    required = [] if is_update else [
        "first_name", "last_name", "email", "phone",
        "department", "designation", "date_of_joining", "salary",
    ]
    for field in required:
        if not data.get(field):
            errors.append(f"'{field}' is required.")

    if data.get("email") and not validate_email(data["email"]):
        errors.append("Invalid email format.")

    if data.get("phone") and not validate_phone(data["phone"]):
        errors.append("Invalid phone number format.")

    if data.get("salary") and float(data.get("salary", 0)) < 0:
        errors.append("Salary cannot be negative.")

    return errors


def validate_leave_request(data):
    errors = []
    for field in ["leave_type", "start_date", "end_date", "reason"]:
        if not data.get(field):
            errors.append(f"'{field}' is required.")
    return errors


def validate_attendance(data):
    errors = []
    if not data.get("employee_id"):
        errors.append("'employee_id' is required.")
    if not data.get("date"):
        errors.append("'date' is required.")
    return errors


def validate_payroll(data):
    errors = []
    for field in ["employee_id", "month", "year"]:
        if not data.get(field):
            errors.append(f"'{field}' is required.")
    month = data.get("month")
    if month and (int(month) < 1 or int(month) > 12):
        errors.append("Month must be between 1 and 12.")
    return errors
