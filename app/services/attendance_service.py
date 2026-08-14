"""
Attendance service — check-in/out, summary, regularization.
"""
from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo
from app.models.attendance_model import AttendanceModel
from app.utils.helpers import parse_date, get_month_date_range


def _col():
    return mongo.db[AttendanceModel.COLLECTION]


def check_in(employee_id, notes=""):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    # Prevent duplicate check-in
    existing = _col().find_one({"employee_id": employee_id, "date": today})
    if existing and existing.get("check_in"):
        return None, "Already checked in today."

    now = datetime.utcnow()
    if existing:
        _col().update_one(
            {"_id": existing["_id"]},
            {"$set": {"check_in": now, "status": "present", "updated_at": now}}
        )
        doc = _col().find_one({"_id": existing["_id"]})
    else:
        doc = AttendanceModel.new(employee_id, today, check_in=now,
                                   status="present", notes=notes)
        result = _col().insert_one(doc)
        doc["_id"] = result.inserted_id

    return AttendanceModel.to_dict(doc), None


def check_out(employee_id):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    record = _col().find_one({"employee_id": employee_id, "date": today})
    if not record:
        return None, "No check-in found for today."
    if record.get("check_out"):
        return None, "Already checked out today."

    now = datetime.utcnow()
    work_hours = 0.0
    if record.get("check_in"):
        delta = now - record["check_in"]
        work_hours = round(delta.total_seconds() / 3600, 2)

    status = "present"
    if work_hours < 4:
        status = "half_day"

    _col().update_one(
        {"_id": record["_id"]},
        {"$set": {
            "check_out": now,
            "work_hours": work_hours,
            "status": status,
            "updated_at": now,
        }}
    )
    doc = _col().find_one({"_id": record["_id"]})
    return AttendanceModel.to_dict(doc), None


def get_attendance_by_date(employee_id, date_str):
    date = parse_date(date_str)
    if not date:
        return None, "Invalid date format. Use YYYY-MM-DD."
    record = _col().find_one({"employee_id": employee_id, "date": date})
    return AttendanceModel.to_dict(record), None


def get_monthly_attendance(employee_id, year, month):
    start, end = get_month_date_range(year, month)
    records = list(_col().find({
        "employee_id": employee_id,
        "date": {"$gte": start, "$lte": end},
    }).sort("date", 1))

    summary = {
        "present": 0, "absent": 0, "half_day": 0,
        "work_from_home": 0, "on_leave": 0, "holiday": 0,
        "total_work_hours": 0.0,
    }
    for r in records:
        s = r.get("status", "absent")
        if s in summary:
            summary[s] += 1
        summary["total_work_hours"] += r.get("work_hours", 0)

    summary["total_work_hours"] = round(summary["total_work_hours"], 2)
    return {
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "records": [AttendanceModel.to_dict(r) for r in records],
        "summary": summary,
    }, None


def get_team_attendance(date_str=None):
    date = parse_date(date_str) if date_str else datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    records = list(_col().find({"date": date}))
    return [AttendanceModel.to_dict(r) for r in records], None


def regularize_attendance(record_id, regularizer_id, check_in_str,
                           check_out_str, status, notes=""):
    check_in = parse_date(check_in_str, "%Y-%m-%dT%H:%M:%S") if check_in_str else None
    check_out = parse_date(check_out_str, "%Y-%m-%dT%H:%M:%S") if check_out_str else None

    work_hours = 0.0
    if check_in and check_out:
        work_hours = round((check_out - check_in).total_seconds() / 3600, 2)

    now = datetime.utcnow()
    result = _col().update_one(
        {"_id": ObjectId(record_id)},
        {"$set": {
            "check_in": check_in,
            "check_out": check_out,
            "work_hours": work_hours,
            "status": status,
            "notes": notes,
            "is_regularized": True,
            "regularized_by": regularizer_id,
            "regularized_at": now,
            "updated_at": now,
        }}
    )
    if result.matched_count == 0:
        return None, "Attendance record not found."
    doc = _col().find_one({"_id": ObjectId(record_id)})
    return AttendanceModel.to_dict(doc), None


def mark_bulk_attendance(records, marked_by):
    """Mark attendance for multiple employees at once."""
    results = []
    for r in records:
        employee_id = r.get("employee_id")
        date = parse_date(r.get("date"))
        status = r.get("status", "present")
        if not employee_id or not date:
            continue
        existing = _col().find_one({"employee_id": employee_id, "date": date})
        now = datetime.utcnow()
        if existing:
            _col().update_one(
                {"_id": existing["_id"]},
                {"$set": {"status": status, "updated_at": now}}
            )
        else:
            doc = AttendanceModel.new(employee_id, date, status=status)
            _col().insert_one(doc)
        results.append(employee_id)
    return results
