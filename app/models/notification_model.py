"""
Notification model.
Stored in MongoDB collection: notifications
"""
from datetime import datetime


class NotificationModel:
    COLLECTION = "notifications"

    TYPES = ["leave_request", "leave_approved", "leave_rejected",
             "payroll_processed", "performance_review", "birthday",
             "work_anniversary", "general"]

    @staticmethod
    def new(recipient_id, title, message, notif_type="general", link=None):
        now = datetime.utcnow()
        return {
            "recipient_id": recipient_id,
            "title": title,
            "message": message,
            "type": notif_type,
            "link": link,
            "is_read": False,
            "created_at": now,
        }

    @staticmethod
    def to_dict(doc):
        if not doc:
            return None
        d = dict(doc)
        d["id"] = str(doc["_id"])
        d.pop("_id", None)
        if d.get("created_at") and isinstance(d["created_at"], datetime):
            d["created_at"] = d["created_at"].isoformat()
        return d
