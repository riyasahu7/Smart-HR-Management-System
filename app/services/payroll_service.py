"""
Payroll service — generate, process, and pay salary slips.
"""
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.models.payroll_model import PayrollModel
from app.models.employee_model import EmployeeModel
from app.models.attendance_model import AttendanceModel
from app.utils.helpers import get_month_date_range


def _col():
    return mongo.db[PayrollModel.COLLECTION]


def _emp_col():
    return mongo.db[EmployeeModel.COLLECTION]


def _att_col():
    return mongo.db[AttendanceModel.COLLECTION]


def _get_worked_days(employee_id, year, month):
    """Count attendance records with status=present or work_from_home."""
    start, end = get_month_date_range(year, month)
    count = _att_col().count_documents({
        "employee_id": employee_id,
        "date": {"$gte": start, "$lte": end},
        "status": {"$in": ["present", "work_from_home"]},
    })
    return count if count > 0 else None  # None means use total_days


def generate_payroll(employee_id, month, year, custom_allowances=None,
                     custom_deductions=None, remarks=""):
    # Prevent duplicate
    existing = _col().find_one({
        "employee_id": employee_id, "month": month, "year": year
    })
    if existing:
        return None, f"Payroll already exists for {year}-{month:02d}."

    emp = _emp_col().find_one({"_id": ObjectId(employee_id)})
    if not emp:
        emp = _emp_col().find_one({"emp_id": employee_id})
    if not emp:
        return None, "Employee not found."

    import calendar
    total_days = calendar.monthrange(year, month)[1]
    worked_days = _get_worked_days(str(emp["_id"]), year, month) or total_days

    basic_salary = emp.get("salary", 0)

    # Default allowances as % of basic
    allowances = {
        "hra": round(basic_salary * 0.40, 2),
        "ta": round(basic_salary * 0.10, 2),
        "da": round(basic_salary * 0.05, 2),
        "medical": 1250.0,
        "other": 0.0,
    }
    if custom_allowances:
        allowances.update(custom_allowances)

    doc = PayrollModel.new(
        employee_id=str(emp["_id"]),
        month=month,
        year=year,
        basic_salary=basic_salary,
        allowances=allowances,
        deductions=custom_deductions,
        worked_days=worked_days,
        total_days=total_days,
    )
    doc["emp_id"] = emp.get("emp_id")
    doc["employee_name"] = emp.get("full_name")
    doc["department"] = emp.get("department")
    doc["designation"] = emp.get("designation")
    doc["remarks"] = remarks

    result = _col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return PayrollModel.to_dict(doc), None


def get_payroll(payroll_id):
    try:
        doc = _col().find_one({"_id": ObjectId(payroll_id)})
    except Exception:
        doc = None
    return PayrollModel.to_dict(doc)


def get_employee_payroll(employee_id, year=None, month=None):
    query = {"employee_id": employee_id}
    if year:
        query["year"] = int(year)
    if month:
        query["month"] = int(month)
    docs = list(_col().find(query).sort([("year", -1), ("month", -1)]))
    return [PayrollModel.to_dict(d) for d in docs]


def get_payroll_list(month, year, department=None, status=None,
                     page=1, per_page=20):
    query = {"month": month, "year": year}
    if department:
        query["department"] = department
    if status:
        query["status"] = status

    total = _col().count_documents(query)
    docs = list(
        _col()
        .find(query)
        .sort("employee_name", 1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return [PayrollModel.to_dict(d) for d in docs], {
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def process_payroll(payroll_id, processor_id):
    """Mark payroll as processed (ready to pay)."""
    now = datetime.utcnow()
    result = _col().update_one(
        {"_id": ObjectId(payroll_id), "status": "draft"},
        {"$set": {"status": "processed", "updated_at": now}}
    )
    if result.matched_count == 0:
        return None, "Payroll not found or already processed."
    doc = _col().find_one({"_id": ObjectId(payroll_id)})
    return PayrollModel.to_dict(doc), None


def mark_paid(payroll_id, payment_mode="bank_transfer"):
    """Mark payroll as paid."""
    now = datetime.utcnow()
    result = _col().update_one(
        {"_id": ObjectId(payroll_id), "status": "processed"},
        {"$set": {"status": "paid", "paid_on": now,
                  "payment_mode": payment_mode, "updated_at": now}}
    )
    if result.matched_count == 0:
        return None, "Payroll not found or not in processed state."
    doc = _col().find_one({"_id": ObjectId(payroll_id)})
    return PayrollModel.to_dict(doc), None


def bulk_generate_payroll(month, year, department=None):
    """Generate payroll for all active employees in a department (or all)."""
    query = {"status": "active"}
    if department:
        query["department"] = department
    employees = list(_emp_col().find(query))
    generated, skipped = [], []
    for emp in employees:
        emp_id = str(emp["_id"])
        doc, err = generate_payroll(emp_id, month, year)
        if err:
            skipped.append({"employee_id": emp_id, "reason": err})
        else:
            generated.append(emp_id)
    return {"generated": len(generated), "skipped": len(skipped), "details": skipped}


def get_payroll_summary(month, year):
    pipeline = [
        {"$match": {"month": month, "year": year}},
        {"$group": {
            "_id": "$department",
            "total_gross": {"$sum": "$gross_salary"},
            "total_net": {"$sum": "$net_salary"},
            "total_deductions": {"$sum": "$total_deductions"},
            "headcount": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    return list(_col().aggregate(pipeline))
