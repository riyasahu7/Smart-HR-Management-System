"""
Notification Routes — Feature 2

GET    /api/notifications              – Get my notifications
GET    /api/notifications/unread-count – Unread notification count
PUT    /api/notifications/<id>/read    – Mark one as read
PUT    /api/notifications/read-all     – Mark all as read
POST   /api/notifications/reminders    – Trigger birthday/anniversary reminders (admin)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.notification_service import (
    get_notifications, mark_read, mark_all_read,
    unread_count, check_and_send_birthday_reminders
)
from app.utils.helpers import success_response, error_response
from app.utils.decorators import admin_required, hr_required

notification_bp = Blueprint("notifications", __name__)


@notification_bp.route("", methods=["GET"])
@jwt_required()
def get_my_notifications():
    user_id = get_jwt_identity()
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = int(request.args.get("limit", 20))
    notifs = get_notifications(user_id, unread_only, limit)
    return jsonify(success_response({"notifications": notifs, "count": len(notifs)})), 200


@notification_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def get_unread_count():
    user_id = get_jwt_identity()
    count = unread_count(user_id)
    return jsonify(success_response({"unread_count": count})), 200


@notification_bp.route("/<notification_id>/read", methods=["PUT"])
@jwt_required()
def mark_one_read(notification_id):
    user_id = get_jwt_identity()
    mark_read(notification_id, user_id)
    return jsonify(success_response(message="Notification marked as read.")), 200


@notification_bp.route("/read-all", methods=["PUT"])
@jwt_required()
def read_all():
    user_id = get_jwt_identity()
    mark_all_read(user_id)
    return jsonify(success_response(message="All notifications marked as read.")), 200


@notification_bp.route("/reminders", methods=["POST"])
@jwt_required()
@hr_required
def trigger_reminders():
    """Manually trigger birthday and work anniversary email reminders."""
    result = check_and_send_birthday_reminders()
    return jsonify(success_response(
        result,
        f"Reminders sent: {result['birthdays']} birthdays, {result['anniversaries']} anniversaries."
    )), 200
