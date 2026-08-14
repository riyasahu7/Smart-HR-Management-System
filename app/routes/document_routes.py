"""
Document Management Routes — Feature 3

GET    /api/documents/<emp_id>           – List employee documents
POST   /api/documents/<emp_id>/upload    – Upload a document
DELETE /api/documents/<emp_id>/<doc_id>  – Delete a document
GET    /api/documents/types              – List allowed document types
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.services.document_service import (
    upload_document, get_documents, delete_document, DOCUMENT_TYPES
)
from app.utils.helpers import success_response, error_response
from app.utils.decorators import hr_required

document_bp = Blueprint("documents", __name__)


@document_bp.route("/types", methods=["GET"])
@jwt_required()
def doc_types():
    return jsonify(success_response(DOCUMENT_TYPES)), 200


@document_bp.route("/<employee_id>", methods=["GET"])
@jwt_required()
def list_documents(employee_id):
    claims = get_jwt()
    # Employees can only view their own documents
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403

    docs = get_documents(employee_id)
    return jsonify(success_response({"documents": docs, "count": len(docs)})), 200


@document_bp.route("/<employee_id>/upload", methods=["POST"])
@jwt_required()
def upload_doc(employee_id):
    claims = get_jwt()
    # Employees can upload their own docs; HR can upload for anyone
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403

    if "document" not in request.files:
        return jsonify(error_response("No file provided. Use field name 'document'.")), 400

    doc_type    = request.form.get("doc_type", "other")
    description = request.form.get("description", "")
    uploaded_by = claims.get("sub") or claims.get("identity", "")

    doc_meta, err = upload_document(
        employee_id,
        request.files["document"],
        doc_type,
        description,
        uploaded_by,
    )
    if err:
        return jsonify(error_response(err)), 400
    return jsonify(success_response(doc_meta, "Document uploaded successfully.")), 201


@document_bp.route("/<employee_id>/<doc_id>", methods=["DELETE"])
@jwt_required()
def delete_doc(employee_id, doc_id):
    claims = get_jwt()
    if claims["role"] == "employee" and claims.get("employee_id") != employee_id:
        return jsonify(error_response("Access denied.", 403)), 403

    ok, err = delete_document(employee_id, doc_id)
    if not ok:
        return jsonify(error_response(err or "Failed to delete.", 404)), 404
    return jsonify(success_response(message="Document deleted.")), 200
