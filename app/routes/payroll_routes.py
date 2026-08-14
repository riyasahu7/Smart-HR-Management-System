"""
Payroll routes.

POST   /api/payroll/generate              – Generate single payroll
POST   /api/payroll/bulk-generate         – Bulk generate for a month
GET    /api/payroll                       – List payroll (month/year filter)
GET    /api/payroll/summary               – Department summary
GET    /api/payroll/employee/<emp_id>     – Employee's salary history
GET    /api/payroll/<id>                  – Single payslip
PUT    /api/payroll/<id>/process          – Mark as processed
PUT    /api/payroll/<id>/pay              – Mark as paid
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services import payroll_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required
from app.utils.validators import validate_payroll

payroll_bp = Blueprint("payroll", __name__)


@payroll_bp.route("/generate", methods=["POST"])
@jwt_required()
@hr_required
def generate():
    data = request.get_json() or {}
    errors = validate_payroll(data)
    if errors:
        return jsonify(error_response("Validation failed.", errors=errors)), 400

    doc, err = payroll_service.generate_payroll(
        employee_id=data["employee_id"],
        month=int(data["month"]),
        year=int(data["year"]),
        custom_allowances=data.get("allowances"),
        custom_deductions=data.get("deductions"),
        remarks=data.get("remarks", ""),
    )
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Payroll generated.", 201)), 201


@payroll_bp.route("/bulk-generate", methods=["POST"])
@jwt_required()
@hr_required
def bulk_generate():
    data = request.get_json() or {}
    if not data.get("month") or not data.get("year"):
        return jsonify(error_response("month and year are required.")), 400
    result = payroll_service.bulk_generate_payroll(
        month=int(data["month"]),
        year=int(data["year"]),
        department=data.get("department"),
    )
    return jsonify(success_response(result, "Bulk payroll generation complete.")), 200


@payroll_bp.route("", methods=["GET"])
@jwt_required()
@hr_required
def list_payroll():
    month = int(request.args.get("month", datetime.now().month))
    year = int(request.args.get("year", datetime.now().year))
    docs, pagination = payroll_service.get_payroll_list(
        month=month, year=year,
        department=request.args.get("department"),
        status=request.args.get("status"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 20)),
    )
    return jsonify(success_response({"payroll": docs, "pagination": pagination})), 200


@payroll_bp.route("/summary", methods=["GET"])
@jwt_required()
@hr_required
def summary():
    month = int(request.args.get("month", 1))
    year = int(request.args.get("year", 2025))
    data = payroll_service.get_payroll_summary(month, year)
    return jsonify(success_response(data)), 200


@payroll_bp.route("/employee/<employee_id>", methods=["GET"])
@jwt_required()
def employee_payroll(employee_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403
    docs = payroll_service.get_employee_payroll(
        employee_id,
        year=request.args.get("year"),
        month=request.args.get("month"),
    )
    return jsonify(success_response(docs)), 200


@payroll_bp.route("/<payroll_id>", methods=["GET"])
@jwt_required()
def get_payslip(payroll_id):
    doc = payroll_service.get_payroll(payroll_id)
    if not doc:
        return jsonify(error_response("Payroll record not found.", 404)), 404
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != doc.get("employee_id"):
        return jsonify(error_response("Access denied.", 403)), 403
    return jsonify(success_response(doc)), 200


@payroll_bp.route("/<payroll_id>/process", methods=["PUT"])
@jwt_required()
@hr_required
def process(payroll_id):
    processor_id = get_jwt_identity()
    doc, err = payroll_service.process_payroll(payroll_id, processor_id)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Payroll processed.")), 200


@payroll_bp.route("/<payroll_id>/pay", methods=["PUT"])
@jwt_required()
@hr_required
def mark_paid(payroll_id):
    data = request.get_json() or {}
    doc, err = payroll_service.mark_paid(payroll_id, data.get("payment_mode", "bank_transfer"))
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc, "Payroll marked as paid.")), 200

