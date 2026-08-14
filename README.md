# Smart HR Management System

A full-stack, role-based HR Management System built with **Flask** and **MongoDB Atlas**, featuring employee records, attendance tracking, leave management, payroll processing, performance reviews, AI-assisted HR support, and automated report generation.

---

## Features

| Module | Capabilities |
|---|---|
| **Authentication** | JWT-based login, role-based access (Admin / HR Manager / Manager / Employee), token refresh |
| **Employee Management** | Create, view, edit, terminate employees; department & headcount analytics |
| **Attendance** | Check-in/out, monthly summary, WFH, regularization by HR |
| **Leave Management** | Apply, approve/reject, cancel; automatic balance deduction per leave type |
| **Payroll** | Auto-calculate gross/net salary with HRA, PF, TDS; bulk generation; Excel export |
| **Performance** | Reviews (annual/mid-year/quarterly), star ratings, goal tracking with progress |
| **AI HR Assistant** | OpenAI GPT chatbot with rule-based fallback for HR policy queries |
| **Reports** | Attendance, leave, payroll, headcount reports with Excel download |
| **Dashboard** | Live stats, Chart.js charts for attendance, department distribution, gender split |

---

## Tech Stack

- **Backend** — Python 3.x, Flask, Flask-JWT-Extended, Flask-PyMongo, Flask-Bcrypt
- **Database** — MongoDB Atlas
- **Frontend** — Jinja2 templates, Vanilla JS, Chart.js, Font Awesome
- **Reports** — openpyxl (Excel export)
- **AI** — OpenAI GPT-3.5 Turbo (with rule-based fallback)

---

## Project Structure

```
Smart-HR-Management-System/
├── app/
│   ├── models/          # MongoDB document schemas
│   ├── routes/          # Flask blueprints (REST API endpoints)
│   ├── services/        # Business logic layer
│   └── utils/           # Helpers, decorators, validators
├── templates/           # Jinja2 HTML templates
│   ├── auth/            # Login page
│   ├── dashboard/       # Dashboard with charts
│   ├── employees/       # List, detail, add/edit
│   ├── attendance/      # Attendance tracker
│   ├── leave/           # Leave requests & balance
│   ├── payroll/         # Payslips & bulk payroll
│   ├── performance/     # Reviews & goals
│   └── reports/         # Report generation
├── static/
│   ├── css/main.css     # Complete UI stylesheet
│   └── js/main.js       # Auth guard, API helpers, AI chat
├── config.py            # Flask configuration
├── run.py               # Application entry point
├── seed.py              # Database seeding script
├── requirement.txt      # Python dependencies
└── .env.example         # Environment variables template
```

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-username/Smart-HR-Management-System.git
cd Smart-HR-Management-System
```

### 2. Install dependencies
```bash
pip install -r requirement.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your MongoDB Atlas URI and secret keys
```

### 4. Seed the database (first time only)
```bash
python seed.py
```

This creates three default users:

| Role | Email | Password |
|---|---|---|
| Admin | admin@smarthr.com | Admin@1234 |
| HR Manager | hr@smarthr.com | Hr@12345 |
| Manager | manager@smarthr.com | Mgr@12345 |

### 5. Run the application
```bash
python run.py
```

Open **http://localhost:5000** in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login and receive JWT tokens |
| GET | `/api/employees` | List employees |
| POST | `/api/employees` | Create employee |
| POST | `/api/attendance/check-in` | Mark check-in |
| POST | `/api/attendance/check-out` | Mark check-out |
| POST | `/api/leave/requests` | Apply for leave |
| PUT | `/api/leave/requests/<id>/review` | Approve / reject leave |
| POST | `/api/payroll/bulk-generate` | Generate payroll for all employees |
| POST | `/api/ai/chat` | AI HR Assistant chat |
| GET | `/api/reports/attendance?format=excel` | Download attendance report |

---

## Roles & Permissions

| Action | Admin | HR Manager | Manager | Employee |
|---|---|---|---|---|
| Manage users | ✅ | ❌ | ❌ | ❌ |
| Create / edit employees | ✅ | ✅ | ❌ | ❌ |
| Process payroll | ✅ | ✅ | ❌ | ❌ |
| Approve leave | ✅ | ✅ | ✅ | ❌ |
| View own data | ✅ | ✅ | ✅ | ✅ |

---

## Environment Variables

See `.env.example` for all required variables. The critical ones:

```env
MONGO_URI=mongodb+srv://...   # MongoDB Atlas connection string
SECRET_KEY=...                # Flask session secret
JWT_SECRET_KEY=...            # JWT signing key
```

---

## License

MIT License — free to use, modify, and distribute.
