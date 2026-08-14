"""
Common helper utilities.
"""
from datetime import datetime, date
from bson import ObjectId
import json
import re


def success_response(data=None, message="Success", status_code=200):
    """Returns just the dict. Routes specify their own HTTP status code."""
    resp = {"success": True, "message": message}
    if data is not None:
        resp["data"] = data
    return resp


def error_response(message="An error occurred", status_code=400, errors=None):
    """Returns just the dict. Routes specify their own HTTP status code."""
    resp = {"success": False, "message": message}
    if errors:
        resp["errors"] = errors
    return resp


def paginate_query(cursor, page=1, per_page=20):
    """Apply skip/limit to a pymongo cursor and return pagination meta."""
    total = cursor.count() if hasattr(cursor, "count") else 0
    items = list(cursor.skip((page - 1) * per_page).limit(per_page))
    return items, {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def validate_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def validate_phone(phone):
    pattern = r"^\+?[0-9]{10,15}$"
    return bool(re.match(pattern, phone))


def parse_date(date_str, fmt="%Y-%m-%d"):
    """Parse a date string into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, fmt)
    except ValueError:
        return None


def serialize_doc(doc):
    """Recursively convert MongoDB doc to JSON-serializable dict."""
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if k == "_id":
                result["id"] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, (datetime, date)):
                result[k] = v.isoformat()
            elif isinstance(v, dict):
                result[k] = serialize_doc(v)
            elif isinstance(v, list):
                result[k] = serialize_doc(v)
            else:
                result[k] = v
        return result
    return doc


def get_month_date_range(year, month):
    """Return (start_date, end_date) for a given year/month."""
    import calendar
    start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59)
    return start, end


def calculate_working_days(start_date, end_date, exclude_weekends=True):
    """Count working days between two dates."""
    from datetime import timedelta
    count = 0
    current = start_date
    while current <= end_date:
        if not exclude_weekends or current.weekday() < 5:  # Mon–Fri
            count += 1
        current += timedelta(days=1)
    return count
