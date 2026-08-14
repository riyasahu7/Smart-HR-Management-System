"""
Report routes.

GET  /api/reports/dashboard-stats         – Key HR metrics
GET  /api/reports/attendance?year&month   – Attendance report (JSON or Excel)
GET  /api/reports/leave?year              – Leave report
GET  /api/reports/payroll?year&month      – Payroll report
GET  /api/reports/headcount               – Headcount trend
"""
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from app.services import report_service
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required, manager_required
from datetime import datetime

report_bp = Blueprint("reports", __name__)


@report_bp.route("/dashboard-stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    data = report_service.get_dashboard_stats()
    return jsonify(success_response(data)), 200


@report_bp.route("/attendance", methods=["GET"])
@jwt_required()
@manager_required
def attendance_report():
    year = int(request.args.get("year", datetime.utcnow().year))
    month = int(request.args.get("month", datetime.utcnow().month))
    department = request.args.get("department")
    fmt = request.args.get("format", "json")

    data = report_service.get_attendance_report(year, month, department)

    if fmt == "excel":
        buf, err = report_service.generate_excel_report("attendance", data)
        if err:
            return jsonify(error_response(err)), 500
        filename = f"attendance_{year}_{month:02d}.xlsx"
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    return jsonify(success_response(data)), 200


@report_bp.route("/leave", methods=["GET"])
@jwt_required()
@hr_required
def leave_report():
    year = int(request.args.get("year", datetime.utcnow().year))
    department = request.args.get("department")
    leave_type = request.args.get("leave_type")
    fmt = request.args.get("format", "json")

    data = report_service.get_leave_report(year, department, leave_type)

    if fmt == "excel":
        buf, err = report_service.generate_excel_report("leave", data)
        if err:
            return jsonify(error_response(err)), 500
        filename = f"leave_report_{year}.xlsx"
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    return jsonify(success_response(data)), 200


@report_bp.route("/payroll", methods=["GET"])
@jwt_required()
@hr_required
def payroll_report():
    year = int(request.args.get("year", datetime.utcnow().year))
    month = int(request.args.get("month", datetime.utcnow().month))
    department = request.args.get("department")
    fmt = request.args.get("format", "json")

    data = report_service.get_payroll_report(year, month, department)

    if fmt == "excel":
        flat = []
        for d in data:
            flat.append({
                "Employee": d.get("employee_name"),
                "Dept": d.get("department"),
                "Basic": d.get("prorated_basic"),
                "Gross": d.get("gross_salary"),
                "Deductions": d.get("total_deductions"),
                "Net": d.get("net_salary"),
                "Status": d.get("status"),
            })
        buf, err = report_service.generate_excel_report("payroll", flat)
        if err:
            return jsonify(error_response(err)), 500
        filename = f"payroll_{year}_{month:02d}.xlsx"
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    return jsonify(success_response(data)), 200


@report_bp.route("/headcount", methods=["GET"])
@jwt_required()
@manager_required
def headcount():
    from app.services.employee_service import get_headcount_trend, get_department_stats
    trend = get_headcount_trend()
    dept = get_department_stats()
    return jsonify(success_response({"trend": trend, "by_department": dept})), 200
