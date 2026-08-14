"""
Leave management service.
"""
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.models.leave_model import LeaveRequestModel, LeaveBalanceModel
from app.utils.helpers import parse_date, get_month_date_range


def _requests():
    return mongo.db[LeaveRequestModel.COLLECTION]


def _balances():
    return mongo.db[LeaveBalanceModel.COLLECTION]


# ── Leave Balance ─────────────────────────────────────────────────────────────

def ensure_leave_balance(employee_id, year=None):
    year = year or datetime.utcnow().year
    existing = _balances().find_one({"employee_id": employee_id, "year": year})
    if not existing:
        doc = LeaveBalanceModel.new(employee_id, year)
        result = _balances().insert_one(doc)
        doc["_id"] = result.inserted_id
        return LeaveBalanceModel.to_dict(doc)
    return LeaveBalanceModel.to_dict(existing)


def get_leave_balance(employee_id, year=None):
    year = year or datetime.utcnow().year
    return ensure_leave_balance(employee_id, year)


# ── Leave Requests ────────────────────────────────────────────────────────────

def apply_leave(employee_id, data):
    leave_type = data.get("leave_type")
    start_date = parse_date(data.get("start_date"))
    end_date = parse_date(data.get("end_date"))
    reason = data.get("reason")
    half_day = bool(data.get("half_day", False))

    if not all([leave_type, start_date, end_date, reason]):
        return None, "leave_type, start_date, end_date, and reason are required."

    if start_date > end_date:
        return None, "start_date must be before or equal to end_date."

    # Check for overlapping leave
    overlap = _requests().find_one({
        "employee_id": employee_id,
        "status": {"$in": ["pending", "approved"]},
        "$or": [
            {"start_date": {"$lte": end_date}, "end_date": {"$gte": start_date}},
        ],
    })
    if overlap:
        return None, "You already have a leave request overlapping these dates."

    # Check balance
    year = start_date.year
    balance = ensure_leave_balance(employee_id, year)
    leave_balance = balance.get(leave_type, {})
    days_requested = (end_date - start_date).days + 1
    if half_day:
        days_requested = 0.5
    if leave_type not in ["unpaid"] and leave_balance.get("remaining", 0) < days_requested:
        return None, (
            f"Insufficient {leave_type} leave balance. "
            f"Available: {leave_balance.get('remaining', 0)} days."
        )

    doc = LeaveRequestModel.new(employee_id, leave_type, start_date, end_date,
                                 reason, half_day)
    result = _requests().insert_one(doc)
    doc["_id"] = result.inserted_id
    return LeaveRequestModel.to_dict(doc), None


def get_leave_requests(employee_id=None, status=None, leave_type=None,
                        page=1, per_page=20, year=None):
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if status:
        query["status"] = status
    if leave_type:
        query["leave_type"] = leave_type
    if year:
        start = datetime(int(year), 1, 1)
        end = datetime(int(year), 12, 31, 23, 59, 59)
        query["start_date"] = {"$gte": start, "$lte": end}

    total = _requests().count_documents(query)
    docs = list(
        _requests()
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return [LeaveRequestModel.to_dict(d) for d in docs], {
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def review_leave(request_id, reviewer_id, action, comments=""):
    """action: 'approved' or 'rejected'"""
    if action not in ("approved", "rejected"):
        return None, "Action must be 'approved' or 'rejected'."

    req = _requests().find_one({"_id": ObjectId(request_id)})
    if not req:
        return None, "Leave request not found."
    if req["status"] != "pending":
        return None, f"Cannot review a request that is already '{req['status']}'."

    now = datetime.utcnow()
    _requests().update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": action,
            "reviewed_by": reviewer_id,
            "reviewed_at": now,
            "reviewer_comments": comments,
            "updated_at": now,
        }}
    )

    # Deduct from balance if approved
    if action == "approved":
        year = req["start_date"].year
        leave_type = req["leave_type"]
        days = req["days_requested"]
        balance = _balances().find_one({"employee_id": req["employee_id"], "year": year})
        if balance and leave_type in balance:
            used = balance[leave_type]["used"] + days
            remaining = max(0, balance[leave_type]["total"] - used)
            _balances().update_one(
                {"_id": balance["_id"]},
                {"$set": {
                    f"{leave_type}.used": used,
                    f"{leave_type}.remaining": remaining,
                    "updated_at": now,
                }}
            )

    doc = _requests().find_one({"_id": ObjectId(request_id)})
    return LeaveRequestModel.to_dict(doc), None


def cancel_leave(request_id, employee_id):
    req = _requests().find_one({
        "_id": ObjectId(request_id),
        "employee_id": employee_id,
    })
    if not req:
        return None, "Leave request not found."
    if req["status"] not in ("pending",):
        return None, "Only pending requests can be cancelled."

    now = datetime.utcnow()
    _requests().update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "cancelled", "updated_at": now}}
    )
    doc = _requests().find_one({"_id": ObjectId(request_id)})
    return LeaveRequestModel.to_dict(doc), None
