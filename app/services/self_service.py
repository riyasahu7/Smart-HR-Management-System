"""
Employee Self-Service Service — Feature 1
Profile updates, payslip PDF, attendance calendar data.
"""
from datetime import datetime
from bson import ObjectId
from app import mongo, bcrypt
from app.models.employee_model import EmployeeModel
from app.models.attendance_model import AttendanceModel
from app.models.payroll_model import PayrollModel
from app.models.leave_model import LeaveRequestModel


def _emp():
    return mongo.db[EmployeeModel.COLLECTION]


def _att():
    return mongo.db[AttendanceModel.COLLECTION]


def _pay():
    return mongo.db[PayrollModel.COLLECTION]


def _leave():
    return mongo.db[LeaveRequestModel.COLLECTION]


# ── Profile Self-Update ───────────────────────────────────────────────────────

def update_own_profile(employee_id, data):
    """
    Employee can update only their own non-sensitive fields.
    HR-only fields (salary, department, designation) are blocked.
    """
    ALLOWED = ["phone", "address", "emergency_contact", "skills",
               "bank_details", "gender", "date_of_birth"]
    update_data = {k: v for k, v in data.items() if k in ALLOWED}

    if not update_data:
        return None, "No valid fields to update."

    update_data["updated_at"] = datetime.utcnow()
    result = _emp().update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None, "Employee record not found."

    doc = _emp().find_one({"_id": ObjectId(employee_id)})
    return EmployeeModel.to_dict(doc), None


# ── Attendance Calendar ───────────────────────────────────────────────────────

def get_attendance_calendar(employee_id, year, month):
    """
    Returns daily attendance status for calendar view.
    Each record: { date, status, check_in, check_out, work_hours }
    """
    from app.utils.helpers import get_month_date_range
    import calendar

    start, end = get_month_date_range(year, month)
    records = list(_att().find({
        "employee_id": employee_id,
        "date": {"$gte": start, "$lte": end},
    }).sort("date", 1))

    record_map = {}
    for r in records:
        if r.get("date"):
            day = r["date"].day
            record_map[day] = {
                "day": day,
                "date": r["date"].strftime("%Y-%m-%d"),
                "status": r.get("status", "absent"),
                "check_in":  r["check_in"].strftime("%H:%M") if r.get("check_in") else None,
                "check_out": r["check_out"].strftime("%H:%M") if r.get("check_out") else None,
                "work_hours": r.get("work_hours", 0),
                "is_regularized": r.get("is_regularized", False),
            }

    # Fill all days
    total_days = calendar.monthrange(year, month)[1]
    calendar_data = []
    for day in range(1, total_days + 1):
        date_obj = datetime(year, month, day)
        is_weekend = date_obj.weekday() >= 5
        if day in record_map:
            entry = record_map[day]
            entry["is_weekend"] = is_weekend
        else:
            entry = {
                "day": day,
                "date": date_obj.strftime("%Y-%m-%d"),
                "status": "holiday" if is_weekend else "absent",
                "check_in": None,
                "check_out": None,
                "work_hours": 0,
                "is_regularized": False,
                "is_weekend": is_weekend,
            }
        calendar_data.append(entry)

    # Summary
    summary = {"present": 0, "absent": 0, "half_day": 0,
                "work_from_home": 0, "on_leave": 0, "total_work_hours": 0}
    for e in calendar_data:
        if not e.get("is_weekend"):
            s = e.get("status", "absent")
            if s in summary:
                summary[s] += 1
            summary["total_work_hours"] += e.get("work_hours", 0)
    summary["total_work_hours"] = round(summary["total_work_hours"], 2)

    return {"calendar": calendar_data, "summary": summary, "year": year, "month": month}


# ── Payslip PDF ───────────────────────────────────────────────────────────────

def generate_payslip_pdf(payroll_id, employee_id):
    """Generate a payslip PDF using fpdf2 (pure Python — works on Vercel)."""
    try:
        from fpdf import FPDF
        import io

        doc_obj = _pay().find_one({"_id": ObjectId(payroll_id)})
        if not doc_obj:
            return None, "Payroll record not found."
        if doc_obj.get("employee_id") != employee_id:
            return None, "Access denied."

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # ── Header ────────────────────────────────────────────────────────────
        pdf.set_fill_color(29, 78, 216)   # Blue
        pdf.rect(0, 0, 210, 28, 'F')
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 14, "Smart HR Management", ln=True, align="C")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 10, f"PAYSLIP  -  {doc_obj.get('pay_period', '')}", ln=True, align="C")
        pdf.ln(6)

        # ── Employee Info ─────────────────────────────────────────────────────
        pdf.set_text_color(30, 41, 59)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, "EMPLOYEE DETAILS", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 10)

        details = [
            ("Employee Name", doc_obj.get("employee_name", "-")),
            ("Department",    doc_obj.get("department", "-")),
            ("Designation",   doc_obj.get("designation", "-")),
            ("Pay Period",    doc_obj.get("pay_period", "-")),
            ("Worked Days",   f"{doc_obj.get('worked_days','-')} / {doc_obj.get('total_days','-')}"),
        ]
        for label, value in details:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(55, 7, label + ":", border="B")
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 7, str(value), border="B", ln=True)
        pdf.ln(5)

        # ── Earnings ──────────────────────────────────────────────────────────
        allow   = doc_obj.get("allowances", {})
        deduct  = doc_obj.get("deductions", {})
        col_w   = 93

        # Headings
        pdf.set_fill_color(29, 78, 216)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_w, 8, "  EARNINGS", fill=True)
        pdf.cell(7, 8, "")
        pdf.cell(col_w, 8, "  DEDUCTIONS", fill=True, ln=True)

        pdf.set_text_color(30, 41, 59)
        pdf.set_font("Helvetica", "", 9)

        earn_rows = [("Basic (Prorated)", doc_obj.get("prorated_basic", 0))]
        for k, v in allow.items():
            if v and v > 0:
                earn_rows.append((k.upper().replace("_", " "), v))

        ded_rows = [(k.upper().replace("_", " "), v)
                    for k, v in deduct.items() if v and v > 0]

        max_r = max(len(earn_rows), len(ded_rows), 1)
        fill = False
        for i in range(max_r):
            pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
            if i < len(earn_rows):
                pdf.cell(col_w, 7, f"  {earn_rows[i][0]}    Rs.{earn_rows[i][1]:,.2f}", fill=True)
            else:
                pdf.cell(col_w, 7, "", fill=True)
            pdf.cell(7, 7, "")
            if i < len(ded_rows):
                pdf.cell(col_w, 7, f"  {ded_rows[i][0]}    Rs.{ded_rows[i][1]:,.2f}", fill=True, ln=True)
            else:
                pdf.cell(col_w, 7, "", fill=True, ln=True)
            fill = not fill

        # Totals row
        pdf.set_fill_color(226, 232, 240)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w, 8, f"  GROSS SALARY    Rs.{doc_obj.get('gross_salary', 0):,.2f}", fill=True)
        pdf.cell(7, 8, "")
        pdf.cell(col_w, 8, f"  TOTAL DEDUCTIONS    Rs.{doc_obj.get('total_deductions', 0):,.2f}", fill=True, ln=True)
        pdf.ln(5)

        # ── Net Payable ───────────────────────────────────────────────────────
        pdf.set_fill_color(240, 253, 244)
        pdf.set_text_color(22, 101, 52)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 12,
                 f"  NET PAYABLE:  Rs.{doc_obj.get('net_salary', 0):,.2f}",
                 fill=True, border=1, ln=True, align="R")

        # ── Footer ────────────────────────────────────────────────────────────
        pdf.ln(8)
        pdf.set_text_color(148, 163, 184)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 6, "This is a system-generated payslip. No signature required.", ln=True, align="C")

        buf = io.BytesIO(pdf.output())
        return buf, None

    except ImportError:
        return None, "fpdf2 not installed. Run: pip install fpdf2"
    except Exception as e:
        return None, str(e)

        buf = io.BytesIO()
        pdf = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Header
        title_style = ParagraphStyle("title", parent=styles["Heading1"],
                                     fontSize=18, textColor=colors.HexColor("#1d4ed8"))
        story.append(Paragraph("Smart HR Management", title_style))
        story.append(Paragraph(f"PAYSLIP — {doc_obj.get('pay_period','')}", styles["Heading2"]))
        story.append(Spacer(1, 0.4*cm))

        # Employee details
        emp_data = [
            ["Employee Name:", doc_obj.get("employee_name", "—")],
            ["Department:",    doc_obj.get("department", "—")],
            ["Designation:",   doc_obj.get("designation", "—")],
            ["Pay Period:",    doc_obj.get("pay_period", "—")],
            ["Worked Days:",   f"{doc_obj.get('worked_days','—')} / {doc_obj.get('total_days','—')}"],
        ]
        emp_table = Table(emp_data, colWidths=[5*cm, 10*cm])
        emp_table.setStyle(TableStyle([
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("TEXTCOLOR", (0,0), (0,-1), colors.grey),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(emp_table)
        story.append(Spacer(1, 0.5*cm))

        # Earnings & Deductions
        allow = doc_obj.get("allowances", {})
        deduct = doc_obj.get("deductions", {})

        earn_rows = [["EARNINGS", "AMOUNT"]]
        earn_rows.append(["Basic (Prorated)", f"₹{doc_obj.get('prorated_basic', 0):,.2f}"])
        for k, v in allow.items():
            if v > 0:
                earn_rows.append([k.upper().replace("_"," "), f"₹{v:,.2f}"])
        earn_rows.append(["GROSS SALARY", f"₹{doc_obj.get('gross_salary', 0):,.2f}"])

        ded_rows = [["DEDUCTIONS", "AMOUNT"]]
        for k, v in deduct.items():
            if v > 0:
                ded_rows.append([k.upper().replace("_"," "), f"₹{v:,.2f}"])
        ded_rows.append(["TOTAL DEDUCTIONS", f"₹{doc_obj.get('total_deductions', 0):,.2f}"])

        max_rows = max(len(earn_rows), len(ded_rows))
        while len(earn_rows) < max_rows: earn_rows.append(["",""])
        while len(ded_rows) < max_rows: ded_rows.append(["",""])

        combined = [[e[0], e[1], d[0], d[1]] for e, d in zip(earn_rows, ded_rows)]
        pay_table = Table(combined, colWidths=[5*cm, 4*cm, 5*cm, 4*cm])
        pay_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME",   (0,-1),(-1,-1),"Helvetica-Bold"),
            ("BACKGROUND", (0,-1),(-1,-1),colors.HexColor("#f0fdf4")),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ]))
        story.append(pay_table)
        story.append(Spacer(1, 0.5*cm))

        # Net
        net_style = ParagraphStyle("net", parent=styles["Heading2"],
                                   textColor=colors.HexColor("#10b981"), fontSize=14)
        story.append(Paragraph(
            f"NET PAYABLE: ₹{doc_obj.get('net_salary', 0):,.2f}", net_style
        ))

        pdf.build(story)
        buf.seek(0)
        return buf, None

    except ImportError:
        return None, "reportlab not installed. Run: pip install reportlab"
    except Exception as e:
        return None, str(e)


# ── Dashboard Summary for Self-Service ───────────────────────────────────────

def get_my_dashboard(employee_id):
    """Aggregate all self-service data for the employee's home view."""
    from app.models.leave_model import LeaveBalanceModel
    from app.utils.helpers import get_month_date_range
    from datetime import timedelta

    today = datetime.utcnow()
    year, month = today.year, today.month

    # This month attendance summary
    start, end = get_month_date_range(year, month)
    att_records = list(_att().find({
        "employee_id": employee_id,
        "date": {"$gte": start, "$lte": end},
    }))
    att_summary = {"present": 0, "absent": 0, "half_day": 0,
                   "work_from_home": 0, "total_work_hours": 0}
    for r in att_records:
        s = r.get("status", "absent")
        if s in att_summary:
            att_summary[s] += 1
        att_summary["total_work_hours"] += r.get("work_hours", 0)
    att_summary["total_work_hours"] = round(att_summary["total_work_hours"], 2)

    # Leave balance
    balance = mongo.db[LeaveBalanceModel.COLLECTION].find_one(
        {"employee_id": employee_id, "year": year}
    )
    leave_summary = {}
    if balance:
        for lt in ["casual", "sick", "earned"]:
            leave_summary[lt] = balance.get(lt, {})

    # Latest payslip
    latest_pay = _pay().find_one(
        {"employee_id": employee_id, "status": {"$in": ["processed", "paid"]}},
        sort=[("year", -1), ("month", -1)]
    )
    payslip = None
    if latest_pay:
        payslip = {
            "pay_period": latest_pay.get("pay_period"),
            "net_salary":  latest_pay.get("net_salary"),
            "id":          str(latest_pay["_id"]),
        }

    # Pending leave requests
    pending_leaves = list(_leave().find({
        "employee_id": employee_id,
        "status": "pending"
    }).limit(3))
    pending = [{"leave_type": l.get("leave_type"),
                "start_date": l["start_date"].strftime("%Y-%m-%d") if l.get("start_date") else "",
                "days": l.get("days_requested")} for l in pending_leaves]

    return {
        "attendance_this_month": att_summary,
        "leave_balance": leave_summary,
        "latest_payslip": payslip,
        "pending_leave_requests": pending,
    }
