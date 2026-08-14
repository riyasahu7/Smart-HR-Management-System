"""
Smart HR — Database Seed Script
Run ONCE after connecting MongoDB Atlas to create the first admin user.

Usage:
    python seed.py

It will create:
  - Admin user:    admin@smarthr.com  / Admin@1234
  - HR Manager:    hr@smarthr.com     / Hr@12345
  - Test Employee: emp@smarthr.com    / Emp@12345
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app, mongo, bcrypt
from app.models.user_model import UserModel
from app.models.employee_model import EmployeeModel
from datetime import datetime

app = create_app("development")

SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@smarthr.com",
        "password": "Admin@1234",
        "role": "admin",
    },
    {
        "username": "hr_manager",
        "email": "hr@smarthr.com",
        "password": "Hr@12345",
        "role": "hr_manager",
    },
    {
        "username": "manager",
        "email": "manager@smarthr.com",
        "password": "Mgr@12345",
        "role": "manager",
    },
]

SEED_EMPLOYEES = [
    {
        "emp_id": "EMP00001",
        "first_name": "Riya",
        "last_name": "Sharma",
        "full_name": "Riya Sharma",
        "email": "riya.sharma@smarthr.com",
        "phone": "+919876543210",
        "department": "Engineering",
        "designation": "Software Engineer",
        "date_of_joining": datetime(2023, 1, 15),
        "salary": 75000,
        "employment_type": "full_time",
        "status": "active",
        "gender": "Female",
        "skills": ["Python", "Flask", "MongoDB"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "address": {}, "emergency_contact": {}, "bank_details": [],
        "documents": [],
    },
    {
        "emp_id": "EMP00002",
        "first_name": "Arjun",
        "last_name": "Patel",
        "full_name": "Arjun Patel",
        "email": "arjun.patel@smarthr.com",
        "phone": "+919876543211",
        "department": "Human Resources",
        "designation": "HR Executive",
        "date_of_joining": datetime(2022, 6, 1),
        "salary": 55000,
        "employment_type": "full_time",
        "status": "active",
        "gender": "Male",
        "skills": ["Recruitment", "Payroll"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "address": {}, "emergency_contact": {}, "bank_details": [],
        "documents": [],
    },
    {
        "emp_id": "EMP00003",
        "first_name": "Priya",
        "last_name": "Mehta",
        "full_name": "Priya Mehta",
        "email": "priya.mehta@smarthr.com",
        "phone": "+919876543212",
        "department": "Finance",
        "designation": "Financial Analyst",
        "date_of_joining": datetime(2021, 9, 10),
        "salary": 65000,
        "employment_type": "full_time",
        "status": "active",
        "gender": "Female",
        "skills": ["Excel", "Accounting", "Tally"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "address": {}, "emergency_contact": {}, "bank_details": [],
        "documents": [],
    },
]

with app.app_context():
    users_col = mongo.db[UserModel.COLLECTION]
    emps_col  = mongo.db[EmployeeModel.COLLECTION]

    print("\n=== Smart HR — Seed Script ===\n")

    # Seed employees first
    emp_ids = {}
    emp_created = 0
    for emp_data in SEED_EMPLOYEES:
        if emps_col.find_one({"email": emp_data["email"]}):
            print(f"  [SKIP] Employee already exists: {emp_data['email']}")
            doc = emps_col.find_one({"email": emp_data["email"]})
            emp_ids[emp_data["email"]] = str(doc["_id"])
        else:
            result = emps_col.insert_one(emp_data)
            emp_ids[emp_data["email"]] = str(result.inserted_id)
            print(f"  [OK]   Employee created: {emp_data['full_name']}  ({emp_data['emp_id']})")
            emp_created += 1

    # Seed users — link to employees where applicable
    user_emp_map = {
        "hr@smarthr.com":      emp_ids.get("arjun.patel@smarthr.com"),
        "manager@smarthr.com": emp_ids.get("riya.sharma@smarthr.com"),
    }

    user_created = 0
    for u in SEED_USERS:
        if users_col.find_one({"email": u["email"]}):
            print(f"  [SKIP] User already exists: {u['email']}")
            continue
        password_hash = bcrypt.generate_password_hash(u["password"]).decode("utf-8")
        doc = UserModel.new(
            username=u["username"],
            email=u["email"],
            password_hash=password_hash,
            role=u["role"],
            employee_id=user_emp_map.get(u["email"]),
        )
        users_col.insert_one(doc)
        print(f"  [OK]   User created: {u['email']}  role={u['role']}  password={u['password']}")
        user_created += 1

    print(f"\n✓ Seed complete — {emp_created} employees, {user_created} users created.\n")
    print("Login credentials:")
    print("  Admin:      admin@smarthr.com   / Admin@1234")
    print("  HR Manager: hr@smarthr.com      / Hr@12345")
    print("  Manager:    manager@smarthr.com / Mgr@12345")
    print()
