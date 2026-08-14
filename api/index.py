"""
Vercel entry point.
Vercel detects Flask via the top-level `app` variable.
Zero-config deployment — vercel.json only needs {"version": 2}.
"""
import sys
import os
import traceback

# Add project root to path so `app` and `config` are importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env for local dev (Vercel uses dashboard env vars in production)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

# Boot the real app — fall back to an error app so Vercel shows what broke
try:
    from app import create_app
    app = create_app("production")

except Exception as _boot_err:
    _detail = traceback.format_exc()
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _error(path):
        return jsonify({
            "error": "App failed to boot",
            "detail": _detail,
            "python": sys.version,
        }), 500
