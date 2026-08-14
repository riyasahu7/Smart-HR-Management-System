"""
Employee management routes.

GET    /api/employees                   – List employees (paginated, filterable)
POST   /api/employees                   – Create employee
GET    /api/employees/stats/departments – Department-wise stats
GET    /api/employees/stats/headcount   – Monthly headcount trend
GET    /api/employees/<id>              – Get single employee
PUT    /api/employees/<id>              – Update employee
DELETE /api/employees/<id>              – Soft-delete (terminate)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.services import employee_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required, manager_required
from app.utils.validators import validate_employee_data

employee_bp = Blueprint("employees", __name__)


@employee_bp.route("", methods=["GET"])
@jwt_required()
def list_employees():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    department = request.args.get("department")
    status = request.args.get("status")
    search = request.args.get("search")
    employment_type = request.args.get("employment_type")

    employees, pagination = employee_service.get_all_employees(
        page, per_page, department, status, search, employment_type
    )
    return jsonify(success_response({"employees": employees, "pagination": pagination})), 200


@employee_bp.route("", methods=["POST"])
@jwt_required()
@hr_required
def create_employee():
    data = request.get_json() or {}
    errors = validate_employee_data(data)
    if errors:
        return jsonify(error_response("Validation failed.", errors=errors)), 400

    emp, err = employee_service.create_employee(data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(emp, "Employee created successfully.", 201)), 201


@employee_bp.route("/stats/departments", methods=["GET"])
@jwt_required()
@manager_required
def department_stats():
    stats = employee_service.get_department_stats()
    return jsonify(success_response(stats)), 200


@employee_bp.route("/stats/headcount", methods=["GET"])
@jwt_required()
@manager_required
def headcount_trend():
    trend = employee_service.get_headcount_trend()
    return jsonify(success_response(trend)), 200


@employee_bp.route("/<employee_id>", methods=["GET"])
@jwt_required()
def get_employee(employee_id):
    claims = get_jwt()
    # Employees can only view their own record unless manager+
    if claims["role"] == "employee":
        emp_id_in_token = claims.get("employee_id")
        emp = employee_service.get_employee(employee_id)
        if emp and emp.get("id") != employee_id and emp_id_in_token != employee_id:
            return jsonify(error_response("Access denied.", 403)), 403

    emp = employee_service.get_employee(employee_id)
    if not emp:
        return jsonify(error_response("Employee not found.", 404)), 404
    return jsonify(success_response(emp)), 200


@employee_bp.route("/<employee_id>", methods=["PUT"])
@jwt_required()
@hr_required
def update_employee(employee_id):
    data = request.get_json() or {}
    errors = validate_employee_data(data, is_update=True)
    if errors:
        return jsonify(error_response("Validation failed.", errors=errors)), 400

    emp, err = employee_service.update_employee(employee_id, data)
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(emp, "Employee updated successfully.")), 200


@employee_bp.route("/<employee_id>", methods=["DELETE"])
@jwt_required()
@hr_required
def delete_employee(employee_id):
    ok = employee_service.delete_employee(employee_id)
    if not ok:
        return jsonify(error_response("Employee not found.", 404)), 404
    return jsonify(success_response(message="Employee terminated successfully.")), 200
