from flask import Blueprint, render_template, jsonify

views_bp = Blueprint("views", __name__)


@views_bp.route("/", defaults={"path": ""})
@views_bp.route("/<path:path>")
def index(path):
    if path.startswith("api/"):
        return jsonify({"ok": False, "message": "Not found"}), 404
    return render_template("index.html")