"""
Authentication routes.

POST   /api/auth/register          – Admin creates a new user
POST   /api/auth/login             – Login and get tokens
POST   /api/auth/refresh           – Refresh access token
GET    /api/auth/me                – Get current user profile
PUT    /api/auth/me                – Update own profile
POST   /api/auth/change-password   – Change own password
GET    /api/auth/users             – Admin: list all users
PUT    /api/auth/users/<id>/role   – Admin: change user role
PUT    /api/auth/users/<id>/status – Admin: activate/deactivate user
POST   /api/auth/users/<id>/reset-password – Admin: reset password
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from app.services import auth_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import admin_required, hr_required

auth_bp = Blueprint("auth", __name__)


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@jwt_required()
@admin_required
def register():
    data = request.get_json() or {}
    required = ["username", "email", "password", "role"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error_response(f"Missing fields: {', '.join(missing)}")[0]), 400

    if len(data["password"]) < 8:
        return jsonify(error_response("Password must be at least 8 characters.")), 400

    user, err = auth_service.register_user(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        role=data["role"],
        employee_id=data.get("employee_id"),
    )
    if err:
        return jsonify(error_response(err)), 400

    return jsonify(success_response(user, "User registered successfully.", 201)), 201


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("password"):
        return jsonify(error_response("Email and password are required.")), 400

    tokens, err = auth_service.login_user(data["email"], data["password"])
    if err:
        return jsonify(error_response(err, 401)), 401

    return jsonify(success_response(tokens, "Login successful.")), 200


# ── Refresh Token ─────────────────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    tokens, err = auth_service.refresh_access_token(user_id)
    if err:
        return jsonify(error_response(err, 401)), 401
    return jsonify(success_response(tokens, "Token refreshed.")), 200


# ── Current User Profile ──────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify(error_response("User not found.", 404)), 404
    return jsonify(success_response(user)), 200


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    user, err = auth_service.update_profile(user_id, data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(user, "Profile updated.")), 200


# ── Change Password ───────────────────────────────────────────────────────────

@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    if not data.get("current_password") or not data.get("new_password"):
        return jsonify(error_response("current_password and new_password are required.")), 400

    ok, err = auth_service.change_password(
        user_id, data["current_password"], data["new_password"]
    )
    if not ok:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(message="Password changed successfully.")), 200


# ── Admin: List Users ─────────────────────────────────────────────────────────

@auth_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def list_users():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    role = request.args.get("role")
    is_active_param = request.args.get("is_active")
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() == "true"

    users, pagination = auth_service.get_all_users(page, per_page, role, is_active)
    return jsonify(success_response({"users": users, "pagination": pagination})), 200


# ── Admin: Change Role ────────────────────────────────────────────────────────

@auth_bp.route("/users/<user_id>/role", methods=["PUT"])
@jwt_required()
@admin_required
def change_role(user_id):
    data = request.get_json() or {}
    new_role = data.get("role")
    if not new_role:
        return jsonify(error_response("'role' is required.")), 400

    ok, err = auth_service.update_user_role(user_id, new_role)
    if not ok:
        return jsonify(error_response(err or "Failed to update role.")), 400
    return jsonify(success_response(message="Role updated successfully.")), 200


# ── Admin: Toggle Status ──────────────────────────────────────────────────────

@auth_bp.route("/users/<user_id>/status", methods=["PUT"])
@jwt_required()
@admin_required
def toggle_status(user_id):
    data = request.get_json() or {}
    if "is_active" not in data:
        return jsonify(error_response("'is_active' boolean is required.")), 400

    ok = auth_service.toggle_user_status(user_id, bool(data["is_active"]))
    if not ok:
        return jsonify(error_response("User not found or no changes made.", 404)), 404
    status_label = "activated" if data["is_active"] else "deactivated"
    return jsonify(success_response(message=f"User {status_label} successfully.")), 200


# ── Admin: Reset Password ─────────────────────────────────────────────────────

@auth_bp.route("/users/<user_id>/reset-password", methods=["POST"])
@jwt_required()
@admin_required
def reset_password(user_id):
    data = request.get_json() or {}
    new_password = data.get("new_password") or auth_service.generate_temp_password()

    ok, err = auth_service.admin_reset_password(user_id, new_password)
    if not ok:
        return jsonify(error_response(err)), 400

    return jsonify(success_response(
        {"temp_password": new_password} if not data.get("new_password") else {},
        "Password reset successfully."
    )), 200
