"""
Employee management service.
"""
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.models.employee_model import EmployeeModel
from app.utils.helpers import parse_date


def _col():
    return mongo.db[EmployeeModel.COLLECTION]


def _next_emp_id():
    count = _col().count_documents({})
    return f"EMP{count + 1:05d}"


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_employee(data):
    doj = parse_date(data.get("date_of_joining"))
    dob = parse_date(data.get("date_of_birth")) if data.get("date_of_birth") else None

    # Check duplicate email
    if _col().find_one({"email": data["email"]}):
        return None, "An employee with this email already exists."

    doc = EmployeeModel.new(
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        phone=data["phone"],
        department=data["department"],
        designation=data["designation"],
        date_of_joining=doj,
        salary=float(data["salary"]),
        manager_id=data.get("manager_id"),
        address=data.get("address"),
        date_of_birth=dob,
        gender=data.get("gender"),
        employment_type=data.get("employment_type", "full_time"),
    )
    doc["emp_id"] = _next_emp_id()
    if data.get("skills"):
        doc["skills"] = data["skills"]
    if data.get("emergency_contact"):
        doc["emergency_contact"] = data["emergency_contact"]
    if data.get("bank_details"):
        doc["bank_details"] = data["bank_details"]

    result = _col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return EmployeeModel.to_dict(doc), None


def get_employee(employee_id):
    try:
        doc = _col().find_one({"_id": ObjectId(employee_id)})
    except Exception:
        doc = _col().find_one({"emp_id": employee_id})
    return EmployeeModel.to_dict(doc)


def get_all_employees(page=1, per_page=20, department=None, status=None,
                      search=None, employment_type=None):
    query = {}
    if department:
        query["department"] = department
    if status:
        query["status"] = status
    if employment_type:
        query["employment_type"] = employment_type
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"emp_id": {"$regex": search, "$options": "i"}},
            {"designation": {"$regex": search, "$options": "i"}},
        ]

    total = _col().count_documents(query)
    docs = list(
        _col()
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return [EmployeeModel.to_dict(d) for d in docs], {
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def update_employee(employee_id, data):
    # Fields HR is allowed to update
    allowed = [
        "first_name", "last_name", "email", "phone", "department",
        "designation", "salary", "manager_id", "address", "date_of_birth",
        "gender", "employment_type", "status", "skills",
        "emergency_contact", "bank_details",
    ]
    update_data = {k: v for k, v in data.items() if k in allowed}
    if not update_data:
        return None, "No valid fields to update."

    if "first_name" in update_data or "last_name" in update_data:
        doc = _col().find_one({"_id": ObjectId(employee_id)})
        if doc:
            fn = update_data.get("first_name", doc.get("first_name", ""))
            ln = update_data.get("last_name", doc.get("last_name", ""))
            update_data["full_name"] = f"{fn} {ln}"

    if "salary" in update_data:
        update_data["salary"] = float(update_data["salary"])

    update_data["updated_at"] = datetime.utcnow()
    result = _col().update_one({"_id": ObjectId(employee_id)}, {"$set": update_data})
    if result.matched_count == 0:
        return None, "Employee not found."
    return get_employee(employee_id), None


def delete_employee(employee_id):
    """Soft-delete: sets status to terminated."""
    result = _col().update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {"status": "terminated", "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


def get_department_stats():
    pipeline = [
        {"$group": {
            "_id": "$department",
            "total": {"$sum": 1},
            "active": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
            "avg_salary": {"$avg": "$salary"},
        }},
        {"$sort": {"total": -1}},
    ]
    return list(mongo.db[EmployeeModel.COLLECTION].aggregate(pipeline))


def get_headcount_trend():
    """Monthly headcount for the last 12 months."""
    pipeline = [
        {"$group": {
            "_id": {
                "year": {"$year": "$date_of_joining"},
                "month": {"$month": "$date_of_joining"},
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
        {"$limit": 12},
    ]
    return list(mongo.db[EmployeeModel.COLLECTION].aggregate(pipeline))
