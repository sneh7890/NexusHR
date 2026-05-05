import json
from flask import Blueprint, request
from flask_jwt_extended import get_current_user
from app.database import query, execute, execute_lastid
from app.utils import ok, err, require_auth, require_role

shared_bp = Blueprint("shared_sheet", __name__)


def _get_or_create_sheet():
    sheet = query("SELECT * FROM shared_sheet ORDER BY id LIMIT 1", fetchone=True)
    if not sheet:
        sid = execute_lastid(
            "INSERT INTO shared_sheet (name, columns, data) VALUES (?,?,?)",
            ("Shared Sheet", json.dumps([]), json.dumps([]))
        )
        sheet = query("SELECT * FROM shared_sheet WHERE id=?", (sid,), fetchone=True)
    r = dict(sheet)
    try:
        r["columns"] = json.loads(r["columns"]) if r.get("columns") else []
    except Exception:
        r["columns"] = []
    return r


def _get_user_rows(sheet_id, user_id):
    try:
        rows = query(
            "SELECT * FROM shared_sheet_rows WHERE sheet_id=? AND user_id=? ORDER BY row_index ASC",
            (sheet_id, user_id), fetchall=True
        )
        return [json.loads(r["data"]) for r in rows]
    except Exception:
        return []


@shared_bp.route("/", methods=["GET"])
@require_auth
def get_sheet():
    user  = get_current_user()
    sheet = _get_or_create_sheet()
    rows  = _get_user_rows(sheet["id"], user["id"])
    return ok({
        "sheet": {
            "id":      sheet["id"],
            "name":    sheet["name"],
            "columns": sheet["columns"],
            "rows":    rows
        }
    })


@shared_bp.route("/save", methods=["POST"])
@require_auth
def save_user_rows():
    user  = get_current_user()
    data  = request.get_json(silent=True) or {}
    rows  = data.get("rows", [])
    sheet = _get_or_create_sheet()
    sid   = sheet["id"]
    uid   = user["id"]
    try:
        execute(
            "DELETE FROM shared_sheet_rows WHERE sheet_id=? AND user_id=?",
            (sid, uid)
        )
        for i, row in enumerate(rows):
            execute_lastid(
                "INSERT INTO shared_sheet_rows (sheet_id, user_id, row_index, data, updated_at) "
                "VALUES (?,?,?,?,datetime('now'))",
                (sid, uid, i, json.dumps(row))
            )
        return ok(message="Saved!")
    except Exception as e:
        return err("Save failed: " + str(e), 500)


@shared_bp.route("/config", methods=["PUT"])
@require_role("admin")
def configure():
    data    = request.get_json(silent=True) or {}
    name    = data.get("name", "Shared Sheet")
    columns = data.get("columns", [])
    if not columns:
        return err("At least one column is required")
    sheet = _get_or_create_sheet()
    execute(
        "UPDATE shared_sheet SET name=?, columns=? WHERE id=?",
        (name, json.dumps(columns), sheet["id"])
    )
    return ok(message="Columns configured!")


@shared_bp.route("/export", methods=["GET"])
@require_auth
def export_csv():
    import csv, io, base64
    user  = get_current_user()
    sheet = _get_or_create_sheet()
    cols  = sheet["columns"]
    rows  = _get_user_rows(sheet["id"], user["id"])
    buf    = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([c["label"] for c in cols])
    for row in rows:
        writer.writerow([row.get(c["key"], "") for c in cols])
    csv_b64  = base64.b64encode(buf.getvalue().encode()).decode()
    filename = "shared_sheet_{}.csv".format(user["full_name"].replace(" ", "_"))
    return ok({"csv_b64": csv_b64, "filename": filename})