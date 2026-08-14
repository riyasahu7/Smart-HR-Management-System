"""
Vercel serverless entry point — with full error trapping.
"""
import sys
import os
import traceback

# Absolute project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Minimal Flask app for error reporting — always works
from flask import Flask, jsonify
_err_app = Flask(__name__)

@_err_app.route("/", defaults={"path": ""})
@_err_app.route("/<path:path>")
def catch_all(path):
    return jsonify({
        "error": "App failed to start",
        "detail": _BOOT_ERROR,
        "root": ROOT,
        "sys_path": sys.path[:5],
    }), 500

_BOOT_ERROR = None

try:
    # Load .env (local dev only — Vercel uses dashboard env vars)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
    except Exception:
        pass

    # Import and create the real app
    from app import create_app
    app = create_app("production")

except Exception:
    _BOOT_ERROR = traceback.format_exc()
    app = _err_app  # Serve error details so we can see what broke
