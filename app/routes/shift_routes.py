"""
Shift & Schedule Management Routes — Feature 5

GET    /api/shifts                          – List all shifts
POST   /api/shifts                          – Create shift
PUT    /api/shifts/<id>                     – Update shift
DELETE /api/shifts/<id>                     – Deactivate shift

GET    /api/shifts/schedules                – All employee schedules
POST   /api/shifts/schedules/assign         – Assign shift to employee
DELETE /api/shifts/schedules/<id>           – Remove schedule
GET    /api/shifts/schedules/employee/<id>  – Employee's schedule
GET    /api/shifts/overtime/<emp_id>        – Overtime report for employee
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services.shift_service import (
    create_shift, get_all_shifts, get_shift, update_shift, delete_shift,
    assign_shift, get_employee_schedule, get_all_schedules,
    remove_schedule, calculate_overtime
)
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required, manager_required
from datetime import datetime

shift_bp = Blueprint("shifts", __name__)


# ── Shift Definitions ─────────────────────────────────────────────────────────

@shift_bp.route("", methods=["GET"])
@jwt_required()
def list_shifts():
    active_only = request.args.get("active_only", "true").lower() != "false"
    shifts = get_all_shifts(active_only)
    return jsonify(success_response({"shifts": shifts, "count": len(shifts)})), 200


@shift_bp.route("", methods=["POST"])
@jwt_required()
@hr_required
def create():
    data = request.get_json() or {}
    shift, err = create_shift(data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(shift, "Shift created.", 201)), 201


@shift_bp.route("/<shift_id>", methods=["GET"])
@jwt_required()
def get_one(shift_id):
    shift = get_shift(shift_id)
    if not shift:
        return jsonify(error_response("Shift not found.", 404)), 404
    return jsonify(success_response(shift)), 200


@shift_bp.route("/<shift_id>", methods=["PUT"])
@jwt_required()
@hr_required
def update(shift_id):
    data = request.get_json() or {}
    shift, err = update_shift(shift_id, data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(shift, "Shift updated.")), 200


@shift_bp.route("/<shift_id>", methods=["DELETE"])
@jwt_required()
@hr_required
def deactivate(shift_id):
    ok = delete_shift(shift_id)
    if not ok:
        return jsonify(error_response("Shift not found.", 404)), 404
    return jsonify(success_response(message="Shift deactivated.")), 200


# ── Schedule Assignment ───────────────────────────────────────────────────────

@shift_bp.route("/schedules", methods=["GET"])
@jwt_required()
@manager_required
def all_schedules():
    docs, pagination = get_all_schedules(
        department=request.args.get("department"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 20)),
    )
    return jsonify(success_response({"schedules": docs, "pagination": pagination})), 200


@shift_bp.route("/schedules/assign", methods=["POST"])
@jwt_required()
@hr_required
def assign():
    data = request.get_json() or {}
    if not data.get("employee_id") or not data.get("shift_id") or not data.get("effective_from"):
        return jsonify(error_response("employee_id, shift_id, and effective_from are required.")), 400

    schedule, err = assign_shift(
        employee_id=data["employee_id"],
        shift_id=data["shift_id"],
        effective_from=data["effective_from"],
        effective_to=data.get("effective_to"),
        notes=data.get("notes", ""),
    )
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(schedule, "Shift assigned successfully.", 201)), 201


@shift_bp.route("/schedules/<schedule_id>", methods=["DELETE"])
@jwt_required()
@hr_required
def remove(schedule_id):
    ok = remove_schedule(schedule_id)
    if not ok:
        return jsonify(error_response("Schedule not found.", 404)), 404
    return jsonify(success_response(message="Schedule removed.")), 200


@shift_bp.route("/schedules/employee/<employee_id>", methods=["GET"])
@jwt_required()
def employee_schedule(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403
    schedules = get_employee_schedule(employee_id)
    return jsonify(success_response({"schedules": schedules})), 200


# ── Overtime ──────────────────────────────────────────────────────────────────

@shift_bp.route("/overtime/<employee_id>", methods=["GET"])
@jwt_required()
def overtime(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403

    now = datetime.utcnow()
    year  = int(request.args.get("year",  now.year))
    month = int(request.args.get("month", now.month))
    data = calculate_overtime(employee_id, year, month)
    return jsonify(success_response(data)), 200
