"""
AI HR Assistant routes.

POST   /api/ai/chat       – Send a message to the HR AI chatbot
GET    /api/ai/insights   – Get AI-generated HR insights
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.services.ai_service import chat_with_ai, get_hr_insights
from app.utils.helpers import success_response, error_response

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify(error_response("'message' is required.")), 400
    if len(message) > 1000:
        return jsonify(error_response("Message too long (max 1000 characters).")[0]), 400

    history = data.get("history", [])
    result = chat_with_ai(message, history)
    return jsonify(success_response(result)), 200


@ai_bp.route("/insights", methods=["GET"])
@jwt_required()
def insights():
    from app.utils.decorators import manager_required
    claims = get_jwt()
    if claims.get("role") not in ("admin", "hr_manager", "manager"):
        return jsonify(error_response("Access denied.", 403)), 403

    data_type = request.args.get("type", "attrition")
    valid_types = ["attrition", "attendance", "performance", "leave"]
    if data_type not in valid_types:
        return jsonify(error_response(
            f"Invalid insight type. Choose from: {', '.join(valid_types)}"
        )[0]), 400

    context = {}
    # Optionally enrich context with live data
    try:
        from app import mongo
        from app.models.performance_model import PerformanceReviewModel
        if data_type == "performance":
            pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$average_rating"}}}]
            result = list(mongo.db[PerformanceReviewModel.COLLECTION].aggregate(pipeline))
            if result:
                context["avg_rating"] = round(result[0]["avg"], 2)
    except Exception:
        pass

    text = get_hr_insights(data_type, context)
    return jsonify(success_response({"insight": text, "type": data_type})), 200
