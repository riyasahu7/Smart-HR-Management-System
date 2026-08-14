"""
Attendance model.
Stored in MongoDB collection: attendance
"""
from datetime import datetime


class AttendanceModel:
    COLLECTION = "attendance"

    STATUS = ["present", "absent", "half_day", "work_from_home", "holiday", "on_leave"]

    @staticmethod
    def new(employee_id, date, check_in=None, check_out=None, status="present", notes=""):
        now = datetime.utcnow()
        work_hours = 0.0
        if check_in and check_out:
            delta = check_out - check_in
            work_hours = round(delta.total_seconds() / 3600, 2)

        return {
            "employee_id": employee_id,
            "date": date,               # datetime (date only)
            "check_in": check_in,       # datetime with time
            "check_out": check_out,
            "work_hours": work_hours,
            "status": status,
            "notes": notes,
            "is_regularized": False,    # HR can regularize missed punches
            "regularized_by": None,
            "regularized_at": None,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def to_dict(doc):
        if not doc:
            return None
        d = dict(doc)
        d["id"] = str(doc["_id"])
        d.pop("_id", None)
        for field in ("date", "check_in", "check_out", "created_at", "updated_at",
                      "regularized_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d
