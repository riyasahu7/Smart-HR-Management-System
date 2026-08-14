"""
Vercel serverless entry point — with full error trapping.

Vercel routes ALL requests (including /static/*) here via vercel.json.
Flask handles static files itself using the absolute static_folder set
in app/__init__.py (works because static/ is bundled via includeFiles).
"""
import sys
import os
import traceback

# Absolute project root — works regardless of Vercel's working directory
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── Fallback error app — always importable, shows boot errors in browser ──────
from flask import Flask, jsonify

_err_app = Flask(__name__)
_BOOT_ERROR = None


@_err_app.route("/", defaults={"path": ""})
@_err_app.route("/<path:path>")
def catch_all(path):
    return jsonify({
        "error": "App failed to start",
        "detail": _BOOT_ERROR,
        "root": ROOT,
        "python": sys.version,
        "sys_path": sys.path[:5],
    }), 500


# ── Real app boot ──────────────────────────────────────────────────────────────
try:
    # Load .env for local dev — Vercel injects env vars from the dashboard
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
    except Exception:
        pass

    from app import create_app
    app = create_app("production")

except Exception:
    _BOOT_ERROR = traceback.format_exc()
    app = _err_app
