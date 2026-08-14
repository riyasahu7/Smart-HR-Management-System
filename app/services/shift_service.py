"""
Shift & Schedule Management Service — Feature 5
Defines shifts, assigns them to employees, calculates overtime.
"""
from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo

SHIFT_COLLECTION = "shifts"
SCHEDULE_COLLECTION = "schedules"


def _shifts():
    return mongo.db[SHIFT_COLLECTION]


def _schedules():
    return mongo.db[SCHEDULE_COLLECTION]


def _emp_col():
    from app.models.employee_model import EmployeeModel
    return mongo.db[EmployeeModel.COLLECTION]


# ── Shift CRUD ────────────────────────────────────────────────────────────────

def create_shift(data):
    """
    data: { name, start_time (HH:MM), end_time (HH:MM),
            break_minutes, days, color, description }
    """
    required = ["name", "start_time", "end_time"]
    for f in required:
        if not data.get(f):
            return None, f"'{f}' is required."

    # Calculate shift duration in hours
    fmt = "%H:%M"
    try:
        start = datetime.strptime(data["start_time"], fmt)
        end   = datetime.strptime(data["end_time"], fmt)
    except ValueError:
        return None, "Invalid time format. Use HH:MM."

    if end < start:          # night shift — crosses midnight
        end += timedelta(hours=24)
    total_mins  = (end - start).seconds // 60
    break_mins  = int(data.get("break_minutes", 30))
    work_hours  = round((total_mins - break_mins) / 60, 2)

    now = datetime.utcnow()
    doc = {
        "name":           data["name"],
        "start_time":     data["start_time"],
        "end_time":       data["end_time"],
        "break_minutes":  break_mins,
        "work_hours":     work_hours,
        "days":           data.get("days", ["Mon","Tue","Wed","Thu","Fri"]),
        "color":          data.get("color", "#3b82f6"),
        "description":    data.get("description", ""),
        "is_active":      True,
        "created_at":     now,
        "updated_at":     now,
    }
    result = _shifts().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_shift(doc), None


def get_all_shifts(active_only=True):
    query = {"is_active": True} if active_only else {}
    docs = list(_shifts().find(query).sort("name", 1))
    return [_serialize_shift(d) for d in docs]


def get_shift(shift_id):
    try:
        doc = _shifts().find_one({"_id": ObjectId(shift_id)})
    except Exception:
        doc = None
    return _serialize_shift(doc)


def update_shift(shift_id, data):
    allowed = ["name", "start_time", "end_time", "break_minutes",
               "days", "color", "description", "is_active"]
    update_data = {k: v for k, v in data.items() if k in allowed}

    if "start_time" in update_data or "end_time" in update_data:
        shift = get_shift(shift_id)
        if shift:
            st = update_data.get("start_time", shift["start_time"])
            et = update_data.get("end_time",   shift["end_time"])
            fmt = "%H:%M"
            try:
                s = datetime.strptime(st, fmt)
                e = datetime.strptime(et, fmt)
                if e < s:
                    e += timedelta(hours=24)
                bk = int(update_data.get("break_minutes", shift.get("break_minutes", 30)))
                update_data["work_hours"] = round(((e - s).seconds // 60 - bk) / 60, 2)
            except Exception:
                pass

    update_data["updated_at"] = datetime.utcnow()
    result = _shifts().update_one({"_id": ObjectId(shift_id)}, {"$set": update_data})
    if result.matched_count == 0:
        return None, "Shift not found."
    return get_shift(shift_id), None


def delete_shift(shift_id):
    result = _shifts().update_one(
        {"_id": ObjectId(shift_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


# ── Schedule Assignment ───────────────────────────────────────────────────────

def assign_shift(employee_id, shift_id, effective_from, effective_to=None, notes=""):
    emp = _emp_col().find_one({"_id": ObjectId(employee_id)})
    if not emp:
        return None, "Employee not found."
    shift = get_shift(shift_id)
    if not shift:
        return None, "Shift not found."

    from app.utils.helpers import parse_date
    eff_from = parse_date(effective_from) if isinstance(effective_from, str) else effective_from
    eff_to   = parse_date(effective_to)   if effective_to and isinstance(effective_to, str) else effective_to

    now = datetime.utcnow()
    doc = {
        "employee_id":    employee_id,
        "emp_id":         emp.get("emp_id"),
        "employee_name":  emp.get("full_name"),
        "department":     emp.get("department"),
        "shift_id":       shift_id,
        "shift_name":     shift["name"],
        "shift_start":    shift["start_time"],
        "shift_end":      shift["end_time"],
        "work_hours":     shift["work_hours"],
        "effective_from": eff_from,
        "effective_to":   eff_to,
        "notes":          notes,
        "is_active":      True,
        "created_at":     now,
        "updated_at":     now,
    }
    result = _schedules().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_schedule(doc), None


def get_employee_schedule(employee_id, active_only=True):
    query = {"employee_id": employee_id}
    if active_only:
        query["is_active"] = True
    docs = list(_schedules().find(query).sort("effective_from", -1))
    return [_serialize_schedule(d) for d in docs]


def get_all_schedules(department=None, page=1, per_page=20):
    query = {"is_active": True}
    if department:
        query["department"] = department
    total = _schedules().count_documents(query)
    docs = list(
        _schedules()
        .find(query)
        .sort("employee_name", 1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return [_serialize_schedule(d) for d in docs], {
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def remove_schedule(schedule_id):
    result = _schedules().update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


# ── Overtime Calculation ──────────────────────────────────────────────────────

def calculate_overtime(employee_id, year, month):
    """
    Compare actual worked hours (from attendance) vs scheduled hours.
    Returns overtime hours per day.
    """
    from app import mongo as m
    from app.models.attendance_model import AttendanceModel
    from app.utils.helpers import get_month_date_range

    start, end = get_month_date_range(year, month)
    schedule = get_employee_schedule(employee_id)
    expected_daily = schedule[0]["work_hours"] if schedule else 8.0

    att_records = list(m.db[AttendanceModel.COLLECTION].find({
        "employee_id": employee_id,
        "date": {"$gte": start, "$lte": end},
    }))

    total_worked   = sum(r.get("work_hours", 0) for r in att_records)
    working_days   = len([r for r in att_records if r.get("status") in ("present", "work_from_home")])
    expected_total = working_days * expected_daily
    overtime_hours = max(0, round(total_worked - expected_total, 2))

    return {
        "employee_id":     employee_id,
        "year":            year,
        "month":           month,
        "total_worked_hours":   round(total_worked, 2),
        "expected_hours":       round(expected_total, 2),
        "overtime_hours":       overtime_hours,
        "working_days":         working_days,
        "expected_daily_hours": expected_daily,
    }


# ── Serializers ───────────────────────────────────────────────────────────────

def _serialize_shift(doc):
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(doc["_id"])
    d.pop("_id", None)
    for f in ("created_at", "updated_at"):
        if d.get(f) and isinstance(d[f], datetime):
            d[f] = d[f].isoformat()
    return d


def _serialize_schedule(doc):
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(doc["_id"])
    d.pop("_id", None)
    for f in ("effective_from", "effective_to", "created_at", "updated_at"):
        if d.get(f) and isinstance(d[f], datetime):
            d[f] = d[f].isoformat()
    return d
