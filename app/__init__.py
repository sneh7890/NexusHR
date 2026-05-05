# import os
# from flask import Flask, jsonify
# from flask_jwt_extended import JWTManager
# from flask_bcrypt import Bcrypt
# from config import get_config
# from app.database import close_db, init_schema, query
#
# bcrypt = Bcrypt()
# jwt    = JWTManager()
#
#
# def create_app():
#     flask_app = Flask(__name__, template_folder="templates", static_folder="static")
#     flask_app.config.from_object(get_config())
#     flask_app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
#
#     bcrypt.init_app(flask_app)
#     jwt.init_app(flask_app)
#
#     flask_app.teardown_appcontext(close_db)
#
#     with flask_app.app_context():
#         init_schema()
#
#     from app.api.auth         import auth_bp
#     from app.api.timesheets   import ts_bp
#     from app.api.admin        import admin_bp
#     from app.api.spreadsheet  import sheet_bp
#     from app.api.shared_sheet import shared_bp
#     from app.views            import views_bp
#
#     flask_app.register_blueprint(auth_bp,   url_prefix="/api/auth")
#     flask_app.register_blueprint(ts_bp,     url_prefix="/api/timesheets")
#     flask_app.register_blueprint(admin_bp,  url_prefix="/api/admin")
#     flask_app.register_blueprint(sheet_bp,  url_prefix="/api/spreadsheet")
#     flask_app.register_blueprint(shared_bp, url_prefix="/api/shared-sheet")
#     flask_app.register_blueprint(views_bp)
#
#     @jwt.user_lookup_loader
#     def user_lookup(jwt_header, jwt_data):
#         uid = jwt_data["sub"]
#         return query(
#             "SELECT * FROM users WHERE id=? AND is_active=1",
#             (uid,), fetchone=True
#         )
#
#     @jwt.invalid_token_loader
#     def invalid_token(reason):
#         return jsonify({"ok": False, "message": "Invalid token"}), 401
#
#     @jwt.unauthorized_loader
#     def missing_token(reason):
#         return jsonify({"ok": False, "message": "Login required"}), 401
#
#     @jwt.expired_token_loader
#     def expired_token(jwt_header, jwt_data):
#         return jsonify({"ok": False, "message": "Token expired"}), 401
#
#     @jwt.revoked_token_loader
#     def revoked_token(jwt_header, jwt_data):
#         return jsonify({"ok": False, "message": "Token revoked"}), 401
#
#     @flask_app.errorhandler(404)
#     def not_found(e):
#         from flask import request
#         if request.path.startswith("/api/"):
#             return jsonify({"ok": False, "message": "Not found"}), 404
#         tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
#         return flask_app.make_response(open(tpl, encoding="utf-8").read()), 200
#
#     @flask_app.errorhandler(405)
#     def method_not_allowed(e):
#         return jsonify({"ok": False, "message": "Method not allowed"}), 405
#
#     @flask_app.errorhandler(500)
#     def server_error(e):
#         import traceback
#         traceback.print_exc()
#         return jsonify({"ok": False, "message": "Server error: " + str(e)}), 500
#
#     return flask_app

import os
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from config import get_config
from app.database import close_db, init_schema, query

bcrypt = Bcrypt()
jwt    = JWTManager()


def create_app():
    flask_app = Flask(__name__, template_folder="templates", static_folder="static")
    flask_app.config.from_object(get_config())
    flask_app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    bcrypt.init_app(flask_app)
    jwt.init_app(flask_app)

    flask_app.teardown_appcontext(close_db)

    with flask_app.app_context():
        init_schema()

    from app.api.auth         import auth_bp
    from app.api.timesheets   import ts_bp
    from app.api.admin        import admin_bp
    from app.api.spreadsheet  import sheet_bp
    from app.api.shared_sheet import shared_bp
    from app.views            import views_bp

    flask_app.register_blueprint(auth_bp,   url_prefix="/api/auth")
    flask_app.register_blueprint(ts_bp,     url_prefix="/api/timesheets")
    flask_app.register_blueprint(admin_bp,  url_prefix="/api/admin")
    flask_app.register_blueprint(sheet_bp,  url_prefix="/api/spreadsheet")
    flask_app.register_blueprint(shared_bp, url_prefix="/api/shared-sheet")
    flask_app.register_blueprint(views_bp)

    @jwt.user_lookup_loader
    def user_lookup(jwt_header, jwt_data):
        uid = jwt_data["sub"]
        return query(
            "SELECT * FROM users WHERE id=? AND is_active=1",
            (uid,), fetchone=True
        )

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"ok": False, "message": "Invalid token"}), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"ok": False, "message": "Login required"}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_data):
        return jsonify({"ok": False, "message": "Token expired"}), 401

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_data):
        return jsonify({"ok": False, "message": "Token revoked"}), 401

    @flask_app.errorhandler(404)
    def not_found(e):
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "message": "Not found"}), 404
        tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
        return flask_app.make_response(open(tpl, encoding="utf-8").read()), 200

    @flask_app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"ok": False, "message": "Method not allowed"}), 405

    @flask_app.errorhandler(500)
    def server_error(e):
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "message": "Server error: " + str(e)}), 500

    # ── Start background scheduler ─────────────────────────────────────────────
    from app.scheduler import start_scheduler
    start_scheduler(flask_app)

    return flask_app