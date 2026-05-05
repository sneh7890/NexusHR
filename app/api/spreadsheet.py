import json
from flask import Blueprint, request
from flask_jwt_extended import get_current_user
from app.database import query, execute, execute_lastid
from app.utils import ok, err, require_auth

sheet_bp = Blueprint("spreadsheet", __name__)

EMPTY_CELL = {"v": "", "bold": False, "italic": False,
              "align": "left", "color": "#212529", "bg": "#ffffff"}


def make_grid(rows=25, cols=10):
    return [[dict(EMPTY_CELL) for _ in range(cols)] for _ in range(rows)]


@sheet_bp.route("/", methods=["GET"])
@require_auth
def list_sheets():
    user = get_current_user()
    rows = query(
        "SELECT id, name, updated_at FROM spreadsheets WHERE user_id=? ORDER BY updated_at DESC",
        (user["id"],), fetchall=True
    )
    return ok({"sheets": rows})


@sheet_bp.route("/", methods=["POST"])
@require_auth
def create_sheet():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "Untitled Sheet")).strip() or "Untitled Sheet"
    sid  = execute_lastid(
        "INSERT INTO spreadsheets (user_id,name,data) VALUES (?,?,?)",
        (user["id"], name, json.dumps(make_grid()))
    )
    return ok({"id": sid, "name": name}, "Sheet created", 201)


@sheet_bp.route("/<int:sid>", methods=["GET"])
@require_auth
def get_sheet(sid):
    user = get_current_user()
    row  = query(
        "SELECT * FROM spreadsheets WHERE id=? AND user_id=?",
        (sid, user["id"]), fetchone=True
    )
    if not row:
        return err("Sheet not found", 404)
    r = dict(row)
    r["data"] = json.loads(r["data"])
    return ok({"sheet": r})


@sheet_bp.route("/<int:sid>", methods=["PUT"])
@require_auth
def save_sheet(sid):
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    execute(
        "UPDATE spreadsheets SET name=?, data=?, updated_at=datetime('now') WHERE id=? AND user_id=?",
        (data.get("name", "Untitled"), json.dumps(data.get("data", [])), sid, user["id"])
    )
    return ok(message="Saved")


@sheet_bp.route("/<int:sid>", methods=["DELETE"])
@require_auth
def delete_sheet(sid):
    user = get_current_user()
    execute("DELETE FROM spreadsheets WHERE id=? AND user_id=?", (sid, user["id"]))
    return ok(message="Deleted")