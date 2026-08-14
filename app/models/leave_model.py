"""
Leave model.
Stored in MongoDB collections: leave_requests, leave_balances
"""
from datetime import datetime


class LeaveRequestModel:
    COLLECTION = "leave_requests"

    LEAVE_TYPES = ["casual", "sick", "earned", "maternity", "paternity",
                   "bereavement", "unpaid", "compensatory"]
    STATUS = ["pending", "approved", "rejected", "cancelled"]

    @staticmethod
    def new(employee_id, leave_type, start_date, end_date, reason, half_day=False):
        now = datetime.utcnow()
        # Calculate working days (simple calc; weekends excluded)
        delta = (end_date - start_date).days + 1
        days_requested = delta * 0.5 if half_day else float(delta)

        return {
            "employee_id": employee_id,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "days_requested": days_requested,
            "half_day": half_day,
            "reason": reason,
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None,
            "reviewer_comments": "",
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
        for field in ("start_date", "end_date", "reviewed_at", "created_at", "updated_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d


class LeaveBalanceModel:
    COLLECTION = "leave_balances"

    @staticmethod
    def new(employee_id, year):
        now = datetime.utcnow()
        return {
            "employee_id": employee_id,
            "year": year,
            "casual": {"total": 12, "used": 0, "remaining": 12},
            "sick": {"total": 10, "used": 0, "remaining": 10},
            "earned": {"total": 15, "used": 0, "remaining": 15},
            "maternity": {"total": 90, "used": 0, "remaining": 90},
            "paternity": {"total": 15, "used": 0, "remaining": 15},
            "bereavement": {"total": 5, "used": 0, "remaining": 5},
            "unpaid": {"total": 999, "used": 0, "remaining": 999},
            "compensatory": {"total": 0, "used": 0, "remaining": 0},
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
        for field in ("created_at", "updated_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d
