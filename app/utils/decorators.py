"""
Custom decorators for role-based access control.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def roles_required(*roles):
    """Decorator to restrict access to specified roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "")
            if user_role not in roles:
                return jsonify({
                    "success": False,
                    "message": f"Access denied. Required roles: {', '.join(roles)}"
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    return roles_required("admin")(fn)


def hr_required(fn):
    return roles_required("admin", "hr_manager")(fn)


def manager_required(fn):
    return roles_required("admin", "hr_manager", "manager")(fn)
