"""
Authentication service — register, login, token management, password reset.
"""
from datetime import datetime
import secrets
import string
from bson import ObjectId
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from app import mongo, bcrypt
from app.models.user_model import UserModel


def _users():
    return mongo.db[UserModel.COLLECTION]


# ── Registration ──────────────────────────────────────────────────────────────

def register_user(username, email, password, role="employee", employee_id=None):
    """Create a new user account. Returns (user_dict, error_str)."""
    # Duplicate checks
    if _users().find_one({"email": email}):
        return None, "Email already registered."
    if _users().find_one({"username": username}):
        return None, "Username already taken."

    if role not in UserModel.ROLES:
        return None, f"Invalid role. Must be one of: {', '.join(UserModel.ROLES)}"

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    doc = UserModel.new(username, email, password_hash, role, employee_id)
    result = _users().insert_one(doc)
    doc["_id"] = result.inserted_id
    return UserModel.to_dict(doc), None


# ── Login ─────────────────────────────────────────────────────────────────────

def login_user(email, password):
    """Validate credentials and return JWT tokens. Returns (tokens_dict, error_str)."""
    user = _users().find_one({"email": email})
    if not user:
        return None, "Invalid email or password."
    if not user.get("is_active"):
        return None, "Account is deactivated. Contact HR."

    if not bcrypt.check_password_hash(user["password_hash"], password):
        return None, "Invalid email or password."

    # Update last login
    _users().update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
    )

    identity = str(user["_id"])
    additional_claims = {
        "role": user["role"],
        "username": user["username"],
        "email": user["email"],
        "employee_id": user.get("employee_id"),
    }

    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": UserModel.to_dict(user),
    }, None


# ── Token Refresh ─────────────────────────────────────────────────────────────

def refresh_access_token(user_id):
    """Issue a new access token from a valid refresh token."""
    user = _users().find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("is_active"):
        return None, "User not found or inactive."

    additional_claims = {
        "role": user["role"],
        "username": user["username"],
        "email": user["email"],
        "employee_id": user.get("employee_id"),
    }
    access_token = create_access_token(identity=user_id, additional_claims=additional_claims)
    return {"access_token": access_token}, None


# ── Profile ───────────────────────────────────────────────────────────────────

def get_user_by_id(user_id):
    user = _users().find_one({"_id": ObjectId(user_id)})
    return UserModel.to_dict(user)


def update_profile(user_id, data):
    """Allow user to update their own username."""
    allowed = ["username"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    if not update_data:
        return None, "No valid fields to update."

    # Username uniqueness
    if "username" in update_data:
        existing = _users().find_one({"username": update_data["username"]})
        if existing and str(existing["_id"]) != user_id:
            return None, "Username already taken."

    update_data["updated_at"] = datetime.utcnow()
    _users().update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    return get_user_by_id(user_id), None


# ── Password Management ───────────────────────────────────────────────────────

def change_password(user_id, current_password, new_password):
    user = _users().find_one({"_id": ObjectId(user_id)})
    if not user:
        return False, "User not found."
    if not bcrypt.check_password_hash(user["password_hash"], current_password):
        return False, "Current password is incorrect."
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters."

    new_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    _users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
    )
    return True, None


def admin_reset_password(target_user_id, new_password):
    """Admin can forcefully reset any user's password."""
    user = _users().find_one({"_id": ObjectId(target_user_id)})
    if not user:
        return False, "User not found."
    new_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    _users().update_one(
        {"_id": ObjectId(target_user_id)},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
    )
    return True, None


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── User Management (Admin) ───────────────────────────────────────────────────

def get_all_users(page=1, per_page=20, role=None, is_active=None):
    query = {}
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active

    total = _users().count_documents(query)
    users = list(
        _users()
        .find(query, {"password_hash": 0})
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return [UserModel.to_dict(u) for u in users], {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def toggle_user_status(target_user_id, is_active):
    result = _users().update_one(
        {"_id": ObjectId(target_user_id)},
        {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


def update_user_role(target_user_id, new_role):
    if new_role not in UserModel.ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(UserModel.ROLES)}"
    result = _users().update_one(
        {"_id": ObjectId(target_user_id)},
        {"$set": {"role": new_role, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0, None
