"""
Payroll model.
Stored in MongoDB collection: payroll
"""
from datetime import datetime


class PayrollModel:
    COLLECTION = "payroll"

    STATUS = ["draft", "processed", "paid", "cancelled"]

    @staticmethod
    def new(employee_id, month, year, basic_salary, allowances=None,
            deductions=None, worked_days=26, total_days=26):
        now = datetime.utcnow()

        allowances = allowances or {
            "hra": 0,           # House Rent Allowance
            "ta": 0,            # Travel Allowance
            "da": 0,            # Dearness Allowance
            "medical": 0,
            "other": 0,
        }
        deductions = deductions or {
            "pf": 0,            # Provident Fund (12% of basic)
            "esi": 0,           # Employee State Insurance
            "professional_tax": 0,
            "tds": 0,           # Tax Deducted at Source
            "loan": 0,
            "advance": 0,
            "other": 0,
        }

        # Prorated salary based on worked days
        prorated_basic = round((basic_salary / total_days) * worked_days, 2)

        # Default PF = 12% of basic
        if deductions["pf"] == 0:
            deductions["pf"] = round(prorated_basic * 0.12, 2)

        gross_salary = prorated_basic + sum(allowances.values())
        total_deductions = sum(deductions.values())
        net_salary = round(gross_salary - total_deductions, 2)

        return {
            "employee_id": employee_id,
            "month": month,
            "year": year,
            "pay_period": f"{year}-{month:02d}",
            "basic_salary": basic_salary,
            "prorated_basic": prorated_basic,
            "worked_days": worked_days,
            "total_days": total_days,
            "allowances": allowances,
            "deductions": deductions,
            "gross_salary": gross_salary,
            "total_deductions": total_deductions,
            "net_salary": net_salary,
            "status": "draft",
            "paid_on": None,
            "payment_mode": "bank_transfer",
            "remarks": "",
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
        for field in ("paid_on", "created_at", "updated_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d
