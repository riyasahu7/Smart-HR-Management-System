"""
Vercel serverless entry point.
Vercel imports this file and uses `app` as the WSGI handler.
"""
import sys
import os

# Resolve the project root directory absolutely
# api/index.py is at <root>/api/index.py, so root = dirname(dirname(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Insert root at the FRONT of sys.path so all project imports work
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Load .env if present (local dev inside Vercel preview)
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "production"))
