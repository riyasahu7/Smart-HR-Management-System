"""
Attendance routes.

POST   /api/attendance/check-in              – Employee checks in
POST   /api/attendance/check-out             – Employee checks out
GET    /api/attendance/today                 – Today's team attendance (HR/manager)
GET    /api/attendance/<emp_id>/date/<date>  – Single day record
GET    /api/attendance/<emp_id>/monthly      – Monthly summary
PUT    /api/attendance/<record_id>/regularize – HR regularizes a record
POST   /api/attendance/bulk                  – Bulk mark attendance
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services import attendance_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required, manager_required

attendance_bp = Blueprint("attendance", __name__)


@attendance_bp.route("/check-in", methods=["POST"])
@jwt_required()
def check_in():
    claims = get_jwt()
    employee_id = claims.get("employee_id") or (request.get_json() or {}).get("employee_id")
    if not employee_id:
        return jsonify(error_response("employee_id is required.")), 400

    # HR/manager can check-in on behalf of employee
    if claims["role"] == "employee":
        employee_id = claims.get("employee_id")

    record, err = attendance_service.check_in(employee_id, (request.get_json() or {}).get("notes", ""))
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(record, "Checked in successfully.")), 200


@attendance_bp.route("/check-out", methods=["POST"])
@jwt_required()
def check_out():
    claims = get_jwt()
    employee_id = claims.get("employee_id") or (request.get_json() or {}).get("employee_id")
    if not employee_id:
        return jsonify(error_response("employee_id is required.")), 400

    if claims["role"] == "employee":
        employee_id = claims.get("employee_id")

    record, err = attendance_service.check_out(employee_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(record, "Checked out successfully.")), 200


@attendance_bp.route("/today", methods=["GET"])
@jwt_required()
@manager_required
def today_attendance():
    date_str = request.args.get("date")
    records, err = attendance_service.get_team_attendance(date_str)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response({"records": records, "count": len(records)})), 200


@attendance_bp.route("/<employee_id>/date/<date_str>", methods=["GET"])
@jwt_required()
def get_by_date(employee_id, date_str):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403

    record, err = attendance_service.get_attendance_by_date(employee_id, date_str)
    if err:
        return jsonify(error_response(err)), 400
    if not record:
        return jsonify(error_response("No record found.", 404)), 404
    return jsonify(success_response(record)), 200


@attendance_bp.route("/<employee_id>/monthly", methods=["GET"])
@jwt_required()
def monthly_summary(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403

    year = int(request.args.get("year", 2025))
    month = int(request.args.get("month", 1))
    data, err = attendance_service.get_monthly_attendance(employee_id, year, month)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(data)), 200


@attendance_bp.route("/<record_id>/regularize", methods=["PUT"])
@jwt_required()
@hr_required
def regularize(record_id):
    data = request.get_json() or {}
    regularizer_id = get_jwt_identity()
    record, err = attendance_service.regularize_attendance(
        record_id=record_id,
        regularizer_id=regularizer_id,
        check_in_str=data.get("check_in"),
        check_out_str=data.get("check_out"),
        status=data.get("status", "present"),
        notes=data.get("notes", ""),
    )
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(record, "Attendance regularized.")), 200


@attendance_bp.route("/bulk", methods=["POST"])
@jwt_required()
@hr_required
def bulk_attendance():
    data = request.get_json() or {}
    records = data.get("records", [])
    if not records:
        return jsonify(error_response("'records' list is required.")), 400
    marked_by = get_jwt_identity()
    result = attendance_service.mark_bulk_attendance(records, marked_by)
    return jsonify(success_response(
        {"marked_count": len(result)}, "Bulk attendance marked."
    )), 200
