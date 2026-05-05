import datetime
from flask import Blueprint, request
from flask_jwt_extended import get_current_user
from app.database import query, execute, execute_lastid
from app.utils import ok, err, require_auth, secs_to_hms, secs_to_decimal, now_str, today_str

ts_bp = Blueprint("timesheets", __name__)


def get_active_ts(user_id):
    return query(
        "SELECT * FROM timesheets WHERE user_id=? AND date=? AND status='active'",
        (user_id, today_str()), fetchone=True
    )


def get_active_break(ts_id):
    return query(
        "SELECT * FROM breaks WHERE timesheet_id=? AND break_out IS NULL",
        (ts_id,), fetchone=True
    )


def break_seconds(ts_id):
    rows = query(
        "SELECT break_in, break_out FROM breaks WHERE timesheet_id=? AND break_out IS NOT NULL",
        (ts_id,), fetchall=True
    )
    total = 0.0
    for r in rows:
        bi = datetime.datetime.fromisoformat(r["break_in"])
        bo = datetime.datetime.fromisoformat(r["break_out"])
        total += (bo - bi).total_seconds()
    return total


def active_break_seconds(ts_id):
    brk = get_active_break(ts_id)
    if not brk:
        return 0.0
    bi = datetime.datetime.fromisoformat(brk["break_in"])
    return (datetime.datetime.now() - bi).total_seconds()


def worked_seconds(ts, include_active_break=True):
    if not ts or not ts.get("clock_in"):
        return 0.0
    ci = datetime.datetime.fromisoformat(ts["clock_in"])
    co_str = ts.get("clock_out")
    co = datetime.datetime.fromisoformat(co_str) if co_str else datetime.datetime.now()
    total  = (co - ci).total_seconds()
    breaks = break_seconds(ts["id"])
    if include_active_break:
        breaks += active_break_seconds(ts["id"])
    return max(0.0, total - breaks)


def serialize_ts(ts):
    w   = worked_seconds(ts, include_active_break=False) if ts.get("clock_out") else worked_seconds(ts)
    brk = break_seconds(ts["id"])
    ci  = ts.get("clock_in")
    co  = ts.get("clock_out")
    return {
        "id":             ts["id"],
        "user_id":        ts.get("user_id"),
        "full_name":      ts.get("full_name", ""),
        "department":     ts.get("department", ""),
        "date":           str(ts.get("date", "")),
        "status":         ts.get("status"),
        "clock_in":       str(ci)[11:16] if ci else None,
        "clock_out":      str(co)[11:16] if co else None,
        "clock_in_full":  str(ci)        if ci else None,
        "clock_out_full": str(co)        if co else None,
        "worked_seconds": w,
        "worked_display": secs_to_hms(w),
        "worked_decimal": secs_to_decimal(w),
        "break_seconds":  brk,
        "break_display":  secs_to_hms(brk),
    }


@ts_bp.route("/status", methods=["GET"])
@require_auth
def status():
    user = get_current_user()
    ts   = get_active_ts(user["id"])
    if not ts:
        return ok({"status": "idle", "worked_seconds": 0, "worked_display": "00:00:00"})
    brk = get_active_break(ts["id"])
    w   = worked_seconds(ts)
    return ok({
        "status":         "on_break" if brk else "clocked_in",
        "clock_in":       ts["clock_in"],
        "worked_seconds": w,
        "worked_display": secs_to_hms(w),
        "ts_id":          ts["id"],
    })


@ts_bp.route("/clock-in", methods=["POST"])
@require_auth
def clock_in():
    user = get_current_user()
    if get_active_ts(user["id"]):
        return err("Already clocked in", 409)
    data     = request.get_json(silent=True) or {}
    timezone = data.get("timezone", user.get("timezone", "IST"))
    execute_lastid(
        "INSERT INTO timesheets (user_id,date,clock_in,timezone) VALUES (?,?,?,?)",
        (user["id"], today_str(), now_str(), timezone)
    )
    execute("UPDATE users SET timezone=? WHERE id=?", (timezone, user["id"]))
    return ok(message="Clocked in successfully!")

@ts_bp.route("/clock-out", methods=["POST"])
@require_auth
def clock_out():
    user = get_current_user()
    ts   = get_active_ts(user["id"])
    if not ts:
        return err("Not clocked in", 400)
    brk = get_active_break(ts["id"])
    now = now_str()
    if brk:
        execute("UPDATE breaks SET break_out=? WHERE id=?", (now, brk["id"]))
    execute(
        "UPDATE timesheets SET clock_out=?, status='completed' WHERE id=?",
        (now, ts["id"])
    )
    ts_updated = query("SELECT * FROM timesheets WHERE id=?", (ts["id"],), fetchone=True)
    w = worked_seconds(ts_updated, include_active_break=False)
    return ok({"worked_seconds": w, "worked_display": secs_to_hms(w)}, "Clocked out!")


@ts_bp.route("/break-in", methods=["POST"])
@require_auth
def break_in():
    user = get_current_user()
    ts   = get_active_ts(user["id"])
    if not ts:
        return err("Not clocked in", 400)
    if get_active_break(ts["id"]):
        return err("Already on break", 409)
    execute_lastid(
        "INSERT INTO breaks (timesheet_id,break_in) VALUES (?,?)",
        (ts["id"], now_str())
    )
    return ok(message="Break started!")


@ts_bp.route("/break-out", methods=["POST"])
@require_auth
def break_out():
    user = get_current_user()
    ts   = get_active_ts(user["id"])
    if not ts:
        return err("Not clocked in", 400)
    brk = get_active_break(ts["id"])
    if not brk:
        return err("Not on break", 400)
    execute("UPDATE breaks SET break_out=? WHERE id=?", (now_str(), brk["id"]))
    return ok(message="Break ended. Back to work!")


@ts_bp.route("/history", methods=["GET"])
@require_auth
def history():
    user  = get_current_user()
    year  = request.args.get("year",  datetime.date.today().year,  type=int)
    month = request.args.get("month", datetime.date.today().month, type=int)
    prefix = "{}-{:02d}-%".format(year, month)
    rows   = query(
        "SELECT * FROM timesheets WHERE user_id=? AND date LIKE ? ORDER BY date DESC",
        (user["id"], prefix), fetchall=True
    )
    records    = [serialize_ts(r) for r in rows]
    total_secs = sum(r["worked_seconds"] for r in records if r.get("clock_out_full"))
    return ok({
        "timesheets":    records,
        "total_seconds": total_secs,
        "total_display": secs_to_hms(total_secs),
    })


@ts_bp.route("/monthly-stats", methods=["GET"])
@require_auth
def monthly_stats():
    user   = get_current_user()
    today  = datetime.date.today()
    prefix = "{}-{:02d}-%".format(today.year, today.month)
    rows   = query(
        "SELECT * FROM timesheets WHERE user_id=? AND date LIKE ?",
        (user["id"], prefix), fetchall=True
    )
    records   = [serialize_ts(r) for r in rows]
    completed = [r for r in records if r.get("clock_out_full")]
    total     = sum(r["worked_seconds"] for r in completed)
    avg       = total / len(completed) if completed else 0
    today_r   = next((r for r in records if r["date"] == str(today)), None)
    today_s   = today_r["worked_seconds"] if today_r else 0
    return ok({
        "days_present":  len(completed),
        "total_seconds": total,
        "total_display": secs_to_hms(total),
        "avg_seconds":   avg,
        "avg_display":   secs_to_hms(avg),
        "today_seconds": today_s,
        "today_display": secs_to_hms(today_s),
    })