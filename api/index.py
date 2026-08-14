"""
Vercel serverless entry point.
Vercel imports this file and calls `app` as the WSGI handler.
"""
import sys
import os

# Make sure the project root is on the path so `app` package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run import app  # noqa: F401  — Vercel needs the `app` symbol
