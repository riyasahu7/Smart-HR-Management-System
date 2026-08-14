"""
Vercel serverless entry point.
"""
import sys
import os

# Absolute path to project root (api/index.py → api/ → root)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env for local/preview — production uses Vercel env vars
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

# Create the Flask app — this is what Vercel uses as the WSGI app
from app import create_app  # noqa: E402

app = create_app("production")


# Debug route — shows environment info (remove after confirming deploy works)
@app.route("/_debug")
def debug():
    from flask import jsonify
    import sys
    return jsonify({
        "status": "ok",
        "python": sys.version,
        "root": ROOT,
        "templates": app.template_folder,
        "static": app.static_folder,
        "env": os.environ.get("FLASK_ENV"),
        "mongo_set": bool(os.environ.get("MONGO_URI")),
        "secret_set": bool(os.environ.get("SECRET_KEY")),
        "routes": len(list(app.url_map.iter_rules())),
    })
