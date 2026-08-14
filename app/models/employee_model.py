"""
Employee model — core HR record.
Stored in MongoDB collection: employees
"""
from datetime import datetime


class EmployeeModel:
    COLLECTION = "employees"

    DEPARTMENTS = [
        "Engineering", "Human Resources", "Finance", "Marketing",
        "Sales", "Operations", "Legal", "Customer Support", "Product",
    ]

    STATUS = ["active", "inactive", "on_leave", "terminated"]

    @staticmethod
    def new(
        first_name, last_name, email, phone, department,
        designation, date_of_joining, salary, manager_id=None,
        address=None, date_of_birth=None, gender=None,
        employment_type="full_time",
    ):
        now = datetime.utcnow()
        emp_id = EmployeeModel._generate_emp_id()
        return {
            "emp_id": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "email": email,
            "phone": phone,
            "department": department,
            "designation": designation,
            "date_of_joining": date_of_joining,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "address": address or {},
            "salary": salary,          # base monthly salary
            "employment_type": employment_type,  # full_time | part_time | contract
            "manager_id": manager_id,
            "status": "active",
            "skills": [],
            "documents": [],           # list of {name, url, uploaded_at}
            "emergency_contact": {},
            "bank_details": {},        # account_no, bank_name, ifsc
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def _generate_emp_id():
        """Generate a time-based employee ID prefix; actual seq added in service."""
        import time
        return f"EMP{int(time.time()) % 100000:05d}"

    @staticmethod
    def to_dict(doc):
        if not doc:
            return None
        d = dict(doc)
        d["id"] = str(doc["_id"])
        d.pop("_id", None)
        # Serialize dates
        for field in ("date_of_joining", "date_of_birth", "created_at", "updated_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d
