"""
Document Management Service — Feature 3
Handles employee document upload, storage (GridFS / local), retrieval.
"""
import os
import uuid
from datetime import datetime
from bson import ObjectId
from werkzeug.utils import secure_filename
from flask import current_app
from app import mongo
from app.models.employee_model import EmployeeModel

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx"}
MAX_FILE_SIZE_MB = 10

DOCUMENT_TYPES = [
    "offer_letter", "id_proof", "address_proof", "pan_card",
    "aadhaar", "degree_certificate", "experience_letter",
    "salary_slip", "passport", "other"
]


def _emp_col():
    return mongo.db[EmployeeModel.COLLECTION]


def _is_serverless():
    """Vercel and other serverless platforms have read-only filesystems."""
    return os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")


def _get_upload_dir():
    # On Vercel /tmp is the only writable dir (ephemeral — lost on redeploy)
    if _is_serverless():
        upload_dir = "/tmp/smart_hr_uploads"
    else:
        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "static", "uploads"
        )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_document(employee_id, file, doc_type, description="", uploaded_by=None):
    """Save file to disk and store metadata in employee's documents array."""
    if not file or file.filename == "":
        return None, "No file selected."
    if not allowed_file(file.filename):
        return None, f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check employee exists
    try:
        emp = _emp_col().find_one({"_id": ObjectId(employee_id)})
    except Exception:
        emp = None
    if not emp:
        return None, "Employee not found."

    # Generate unique filename
    ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
    unique_name = f"{employee_id}_{uuid.uuid4().hex[:8]}.{ext}"
    upload_dir = _get_upload_dir()
    save_path = os.path.join(upload_dir, unique_name)
    file.save(save_path)

    doc_meta = {
        "doc_id": str(uuid.uuid4()),
        "doc_type": doc_type,
        "original_name": secure_filename(file.filename),
        "stored_name": unique_name,
        "url": f"/static/uploads/{unique_name}",
        "description": description,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.utcnow().isoformat(),
        "size_kb": round(os.path.getsize(save_path) / 1024, 1),
    }

    _emp_col().update_one(
        {"_id": ObjectId(employee_id)},
        {
            "$push": {"documents": doc_meta},
            "$set": {"updated_at": datetime.utcnow()},
        }
    )
    return doc_meta, None


def get_documents(employee_id):
    """Return all documents for an employee."""
    try:
        emp = _emp_col().find_one({"_id": ObjectId(employee_id)}, {"documents": 1})
    except Exception:
        emp = None
    if not emp:
        return []
    return emp.get("documents", [])


def delete_document(employee_id, doc_id):
    """Remove a document record and its file from disk."""
    try:
        emp = _emp_col().find_one({"_id": ObjectId(employee_id)}, {"documents": 1})
    except Exception:
        return False, "Employee not found."

    if not emp:
        return False, "Employee not found."

    doc = next((d for d in emp.get("documents", []) if d["doc_id"] == doc_id), None)
    if not doc:
        return False, "Document not found."

    # Delete physical file
    file_path = os.path.join(_get_upload_dir(), doc["stored_name"])
    if os.path.exists(file_path):
        os.remove(file_path)

    _emp_col().update_one(
        {"_id": ObjectId(employee_id)},
        {"$pull": {"documents": {"doc_id": doc_id}}}
    )
    return True, None


def upload_profile_photo(employee_id, file):
    """Upload and save profile photo, store URL on employee record."""
    if not file or file.filename == "":
        return None, "No file selected."
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        return None, "Only PNG, JPG, JPEG, WEBP allowed for profile photo."

    # Use /tmp on Vercel (read-only filesystem), local static dir otherwise
    if _is_serverless():
        photos_dir = "/tmp/smart_hr_photos"
    else:
        photos_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "static", "uploads", "photos"
        )
    os.makedirs(photos_dir, exist_ok=True)

    filename = f"photo_{employee_id}.{ext}"
    save_path = os.path.join(photos_dir, filename)
    file.save(save_path)

    # URL: /tmp files aren't web-served, so store a relative path for local
    # and a placeholder note for serverless (photo feature requires object storage in prod)
    url = f"/static/uploads/photos/{filename}"

    _emp_col().update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {"photo_url": url, "updated_at": datetime.utcnow()}}
    )
    return url, None
