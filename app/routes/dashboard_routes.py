"""
Dashboard routes — serve the main HTML pages.
All API data is fetched client-side from /api/* endpoints.
"""
from flask import Blueprint, render_template, redirect, url_for

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    return redirect(url_for("dashboard.login_page"))


@dashboard_bp.route("/login")
def login_page():
    return render_template("auth/login.html")


@dashboard_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard/index.html")


@dashboard_bp.route("/employees")
def employees():
    return render_template("employees/list.html")


@dashboard_bp.route("/employees/new")
def new_employee():
    return render_template("employees/form.html", mode="create")


@dashboard_bp.route("/employees/<employee_id>")
def employee_detail(employee_id):
    return render_template("employees/detail.html", employee_id=employee_id)


@dashboard_bp.route("/employees/<employee_id>/edit")
def edit_employee(employee_id):
    return render_template("employees/form.html", mode="edit", employee_id=employee_id)


@dashboard_bp.route("/attendance")
def attendance():
    return render_template("attendance/index.html")


@dashboard_bp.route("/leave")
def leave():
    return render_template("leave/index.html")


@dashboard_bp.route("/payroll")
def payroll():
    return render_template("payroll/index.html")


@dashboard_bp.route("/performance")
def performance():
    return render_template("performance/index.html")


@dashboard_bp.route("/reports")
def reports():
    return render_template("reports/index.html")
