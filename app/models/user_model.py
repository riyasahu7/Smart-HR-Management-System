"""
User model — authentication and role management.
Stored in MongoDB collection: users
"""
from datetime import datetime
from bson import ObjectId


class UserModel:
    COLLECTION = "users"

    ROLES = ["admin", "hr_manager", "manager", "employee"]

    SCHEMA = {
        "username": str,
        "email": str,
        "password_hash": str,
        "role": str,          # admin | hr_manager | manager | employee
        "employee_id": str,   # linked employee document
        "is_active": bool,
        "last_login": datetime,
        "created_at": datetime,
        "updated_at": datetime,
    }

    @staticmethod
    def new(username, email, password_hash, role="employee", employee_id=None):
        now = datetime.utcnow()
        return {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "employee_id": employee_id,
            "is_active": True,
            "last_login": None,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def to_dict(user_doc):
        """Serialize a MongoDB user document to a safe dict (no password)."""
        if not user_doc:
            return None
        return {
            "id": str(user_doc["_id"]),
            "username": user_doc.get("username"),
            "email": user_doc.get("email"),
            "role": user_doc.get("role"),
            "employee_id": user_doc.get("employee_id"),
            "is_active": user_doc.get("is_active"),
            "last_login": (
                user_doc["last_login"].isoformat()
                if user_doc.get("last_login")
                else None
            ),
            "created_at": (
                user_doc["created_at"].isoformat()
                if user_doc.get("created_at")
                else None
            ),
        }
