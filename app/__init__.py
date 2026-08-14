from flask import Flask
from flask_jwt_extended import JWTManager
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_cors import CORS
from config import config

mongo = PyMongo()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()


def create_app(config_name="default"):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config[config_name])

    # Extensions
    mongo.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    CORS(app)

    # ── Global error handlers ─────────────────────────
    from flask import jsonify
    import pymongo.errors

    @app.errorhandler(pymongo.errors.OperationFailure)
    def handle_mongo_auth_error(e):
        return jsonify({
            "success": False,
            "message": "Database authentication failed. Check MONGO_URI credentials in .env",
            "error": str(e)
        }), 503

    @app.errorhandler(pymongo.errors.ServerSelectionTimeoutError)
    def handle_mongo_timeout(e):
        return jsonify({
            "success": False,
            "message": "Cannot connect to MongoDB. Check your MONGO_URI and network.",
            "error": str(e)
        }), 503

    @app.errorhandler(404)
    def not_found(e):
        from flask import request as req
        if req.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Endpoint not found."}), 404
        return jsonify({"success": False, "message": "Page not found."}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "message": "Internal server error.", "error": str(e)}), 500

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.employee_routes import employee_bp
    from app.routes.attendance_routes import attendance_bp
    from app.routes.leave_routes import leave_bp
    from app.routes.payroll_routes import payroll_bp
    from app.routes.performance_routes import performance_bp
    from app.routes.ai_routes import ai_bp
    from app.routes.report_routes import report_bp
    from app.routes.dashboard_routes import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(employee_bp, url_prefix="/api/employees")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
    app.register_blueprint(leave_bp, url_prefix="/api/leave")
    app.register_blueprint(payroll_bp, url_prefix="/api/payroll")
    app.register_blueprint(performance_bp, url_prefix="/api/performance")
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    app.register_blueprint(report_bp, url_prefix="/api/reports")
    app.register_blueprint(dashboard_bp, url_prefix="/")

    return app
