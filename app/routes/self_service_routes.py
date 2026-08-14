"""
Employee Self-Service Routes — Feature 1

GET    /api/self/profile               – Get own employee profile
PUT    /api/self/profile               – Update own profile fields
POST   /api/self/profile/photo         – Upload profile photo
GET    /api/self/attendance/calendar   – Monthly attendance calendar
GET    /api/self/payslips              – List own payslips
GET    /api/self/payslips/<id>/pdf     – Download payslip as PDF
GET    /api/self/dashboard             – Self-service summary dashboard
"""
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services import self_service, document_service
from app.utils.helpers import success_response, error_response
from datetime import datetime

self_service_bp = Blueprint("self_service", __name__)


@self_service_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked to this account.", 404)), 404

    from app import mongo
    from app.models.employee_model import EmployeeModel
    from bson import ObjectId
    emp = mongo.db[EmployeeModel.COLLECTION].find_one({"_id": ObjectId(emp_id)})
    if not emp:
        return jsonify(error_response("Employee record not found.", 404)), 404
    return jsonify(success_response(EmployeeModel.to_dict(emp))), 200


@self_service_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked to this account.", 404)), 404

    data = request.get_json() or {}
    result, err = self_service.update_own_profile(emp_id, data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(result, "Profile updated successfully.")), 200


@self_service_bp.route("/profile/photo", methods=["POST"])
@jwt_required()
def upload_photo():
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked.", 404)), 404

    if "photo" not in request.files:
        return jsonify(error_response("No file in request. Use field name 'photo'.")), 400

    url, err = document_service.upload_profile_photo(emp_id, request.files["photo"])
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response({"photo_url": url}, "Photo uploaded.")), 200


@self_service_bp.route("/attendance/calendar", methods=["GET"])
@jwt_required()
def attendance_calendar():
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked.", 404)), 404

    now = datetime.utcnow()
    year  = int(request.args.get("year",  now.year))
    month = int(request.args.get("month", now.month))
    data = self_service.get_attendance_calendar(emp_id, year, month)
    return jsonify(success_response(data)), 200


@self_service_bp.route("/payslips", methods=["GET"])
@jwt_required()
def list_payslips():
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked.", 404)), 404

    from app import mongo
    from app.models.payroll_model import PayrollModel
    year = request.args.get("year")
    query = {"employee_id": emp_id, "status": {"$in": ["processed", "paid"]}}
    if year:
        query["year"] = int(year)
    docs = list(mongo.db[PayrollModel.COLLECTION].find(query).sort([("year", -1), ("month", -1)]))
    return jsonify(success_response([PayrollModel.to_dict(d) for d in docs])), 200


@self_service_bp.route("/payslips/<payroll_id>/pdf", methods=["GET"])
@jwt_required()
def download_payslip_pdf(payroll_id):
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked.", 404)), 404

    buf, err = self_service.generate_payslip_pdf(payroll_id, emp_id)
    if err:
        return jsonify(error_response(err)), 400
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"payslip_{payroll_id}.pdf"
    )


@self_service_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def my_dashboard():
    claims = get_jwt()
    emp_id = claims.get("employee_id")
    if not emp_id:
        return jsonify(error_response("No employee record linked.", 404)), 404

    data = self_service.get_my_dashboard(emp_id)
    return jsonify(success_response(data)), 200
