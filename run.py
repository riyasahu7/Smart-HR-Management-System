"""
Smart HR Management System — Entry Point

Local dev  : python run.py
Vercel     : auto-detected via api/index.py → run:app
"""
import os
from app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=(env == "development"),
    )
