"""
Leave management routes.

GET    /api/leave/balance/<emp_id>     – Get leave balance
GET    /api/leave/requests             – List leave requests (HR sees all, employee sees own)
POST   /api/leave/requests             – Apply for leave
GET    /api/leave/requests/<id>        – Single request detail
PUT    /api/leave/requests/<id>/review – HR/manager approves or rejects
PUT    /api/leave/requests/<id>/cancel – Employee cancels pending request
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services import leave_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required, manager_required
from app.utils.validators import validate_leave_request

leave_bp = Blueprint("leave", __name__)


@leave_bp.route("/balance/<employee_id>", methods=["GET"])
@jwt_required()
def get_balance(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403
    year = request.args.get("year")
    balance = leave_service.get_leave_balance(employee_id, int(year) if year else None)
    return jsonify(success_response(balance)), 200


@leave_bp.route("/requests", methods=["GET"])
@jwt_required()
def list_requests():
    claims = get_jwt()
    # Employees only see their own
    employee_id = None
    if claims["role"] == "employee":
        employee_id = claims.get("employee_id")
    else:
        employee_id = request.args.get("employee_id")

    data, pagination = leave_service.get_leave_requests(
        employee_id=employee_id,
        status=request.args.get("status"),
        leave_type=request.args.get("leave_type"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 20)),
        year=request.args.get("year"),
    )
    return jsonify(success_response({"requests": data, "pagination": pagination})), 200


@leave_bp.route("/requests", methods=["POST"])
@jwt_required()
def apply_leave():
    claims = get_jwt()
    data = request.get_json() or {}
    errors = validate_leave_request(data)
    if errors:
        return jsonify(error_response("Validation failed.", errors=errors)), 400

    # Employees apply for themselves
    if claims["role"] == "employee":
        data["employee_id"] = claims.get("employee_id")
    if not data.get("employee_id"):
        return jsonify(error_response("employee_id is required.")), 400

    result, err = leave_service.apply_leave(data["employee_id"], data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(result, "Leave request submitted.", 201)), 201


@leave_bp.route("/requests/<request_id>", methods=["GET"])
@jwt_required()
def get_request(request_id):
    from app import mongo
    from app.models.leave_model import LeaveRequestModel
    from bson import ObjectId
    doc = mongo.db[LeaveRequestModel.COLLECTION].find_one({"_id": ObjectId(request_id)})
    if not doc:
        return jsonify(error_response("Request not found.", 404)), 404
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != doc.get("employee_id"):
        return jsonify(error_response("Access denied.", 403)), 403
    return jsonify(success_response(LeaveRequestModel.to_dict(doc))), 200


@leave_bp.route("/requests/<request_id>/review", methods=["PUT"])
@jwt_required()
@manager_required
def review_request(request_id):
    data = request.get_json() or {}
    action = data.get("action")
    if action not in ("approved", "rejected"):
        return jsonify(error_response("'action' must be 'approved' or 'rejected'.")), 400

    reviewer_id = get_jwt_identity()
    result, err = leave_service.review_leave(
        request_id, reviewer_id, action, data.get("comments", "")
    )
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(result, f"Leave request {action}.")), 200


@leave_bp.route("/requests/<request_id>/cancel", methods=["PUT"])
@jwt_required()
def cancel_request(request_id):
    claims = get_jwt()
    employee_id = claims.get("employee_id")
    if not employee_id:
        return jsonify(error_response("Employee ID not found in token.")), 400

    result, err = leave_service.cancel_leave(request_id, employee_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(result, "Leave request cancelled.")), 200
