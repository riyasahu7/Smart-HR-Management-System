"""
Performance routes.

GET    /api/performance/reviews                   – List all reviews (HR/manager)
POST   /api/performance/reviews                   – Create review
GET    /api/performance/reviews/<id>              – Get review
PUT    /api/performance/reviews/<id>              – Update review
POST   /api/performance/reviews/<id>/submit       – Submit for acknowledgement
POST   /api/performance/reviews/<id>/acknowledge  – Employee acknowledges
GET    /api/performance/employee/<id>/reviews     – Employee's review history
GET    /api/performance/employee/<id>/analytics   – Rating trend
GET    /api/performance/goals                     – Employee's goals
POST   /api/performance/goals                     – Create goal
PUT    /api/performance/goals/<id>                – Update goal progress
POST   /api/performance/goals/<id>/comment        – Add comment on goal
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services import performance_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required, manager_required

performance_bp = Blueprint("performance", __name__)


@performance_bp.route("/reviews", methods=["GET"])
@jwt_required()
@manager_required
def list_reviews():
    docs, pagination = performance_service.get_all_reviews(
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 20)),
        department=request.args.get("department"),
        status=request.args.get("status"),
        review_type=request.args.get("review_type"),
        employee_id=request.args.get("employee_id"),
    )
    return jsonify(success_response({"reviews": docs, "pagination": pagination})), 200


@performance_bp.route("/reviews", methods=["POST"])
@jwt_required()
@manager_required
def create_review():
    data = request.get_json() or {}
    reviewer_id = get_jwt_identity()
    doc, err = performance_service.create_review(data, reviewer_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Review created.", 201)), 201


@performance_bp.route("/reviews/<review_id>", methods=["GET"])
@jwt_required()
def get_review(review_id):
    doc = performance_service.get_review(review_id)
    if not doc:
        return jsonify(error_response("Review not found.", 404)), 404
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != doc.get("employee_id"):
        return jsonify(error_response("Access denied.", 403)), 403
    return jsonify(success_response(doc)), 200


@performance_bp.route("/reviews/<review_id>", methods=["PUT"])
@jwt_required()
@manager_required
def update_review(review_id):
    data = request.get_json() or {}
    doc, err = performance_service.update_review(review_id, data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Review updated.")), 200


@performance_bp.route("/reviews/<review_id>/submit", methods=["POST"])
@jwt_required()
@manager_required
def submit_review(review_id):
    doc, err = performance_service.submit_review(review_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Review submitted.")), 200


@performance_bp.route("/reviews/<review_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_review(review_id):
    claims = get_jwt()
    employee_id = claims.get("employee_id")
    if not employee_id:
        return jsonify(error_response("Employee ID not in token.", 400)), 400
    doc, err = performance_service.acknowledge_review(review_id, employee_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Review acknowledged.")), 200


@performance_bp.route("/employee/<employee_id>/reviews", methods=["GET"])
@jwt_required()
def employee_reviews(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403
    docs = performance_service.get_employee_reviews(
        employee_id,
        review_type=request.args.get("review_type"),
        status=request.args.get("status"),
    )
    return jsonify(success_response(docs)), 200


@performance_bp.route("/employee/<employee_id>/analytics", methods=["GET"])
@jwt_required()
def analytics(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403
    data = performance_service.get_performance_analytics(employee_id)
    return jsonify(success_response(data)), 200


@performance_bp.route("/goals", methods=["GET"])
@jwt_required()
def list_goals():
    claims = get_jwt()
    employee_id = claims.get("employee_id") if claims["role"] == "employee" \
        else request.args.get("employee_id")
    if not employee_id:
        return jsonify(error_response("employee_id is required.", 400)), 400
    docs = performance_service.get_employee_goals(
        employee_id, status=request.args.get("status")
    )
    return jsonify(success_response(docs)), 200


@performance_bp.route("/goals", methods=["POST"])
@jwt_required()
def create_goal():
    data = request.get_json() or {}
    creator_id = get_jwt_identity()
    claims = get_jwt()
    if claims["role"] == "employee":
        data["employee_id"] = claims.get("employee_id")
    doc, err = performance_service.create_goal(data, creator_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Goal created.", 201)), 201


@performance_bp.route("/goals/<goal_id>", methods=["PUT"])
@jwt_required()
def update_goal(goal_id):
    data = request.get_json() or {}
    doc, err = performance_service.update_goal(goal_id, data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Goal updated.")), 200


@performance_bp.route("/goals/<goal_id>/comment", methods=["POST"])
@jwt_required()
def goal_comment(goal_id):
    data = request.get_json() or {}
    text = data.get("text")
    if not text:
        return jsonify(error_response("'text' is required.")), 400
    author_id = get_jwt_identity()
    doc = performance_service.add_goal_comment(goal_id, author_id, text)
    return jsonify(success_response(doc, "Comment added.")), 200
