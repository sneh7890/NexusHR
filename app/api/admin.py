# import csv
# import io
# import base64
# import datetime
# from flask import Blueprint, request
# from flask_jwt_extended import get_current_user
# from flask_bcrypt import Bcrypt
# from app.database import query, execute, execute_lastid
# from app.utils import ok, err, require_role, secs_to_hms, secs_to_decimal
# from app.api.timesheets import serialize_ts, break_seconds, worked_seconds
#
# admin_bp = Blueprint("admin", __name__)
# bcrypt   = Bcrypt()
# ROLES    = ("admin", "manager", "employee")
#
#
# def safe_user(u):
#     if not u:
#         return None
#     return {
#         "id":          u["id"],
#         "username":    u["username"],
#         "email":       u["email"],
#         "full_name":   u["full_name"],
#         "role":        u["role"],
#         "department":  u["department"],
#         "shift_start": u["shift_start"],
#         "shift_end":   u["shift_end"],
#         "is_active":   bool(u["is_active"]),
#         "created_at":  u["created_at"],
#         "photo":       u.get("photo", None)
#     }
#
#
# @admin_bp.route("/overview", methods=["GET"])
# @require_role("admin", "manager")
# def overview():
#     today = datetime.date.today().isoformat()
#
#     # Total active employees + managers (everyone except admin)
#     total_emp = query(
#         "SELECT COUNT(*) AS c FROM users WHERE role IN ('employee','manager') AND is_active=1",
#         fetchone=True
#     )["c"]
#
#     # Clocked in today (active timesheet, not clocked out yet)
#     clocked_in = query(
#         "SELECT COUNT(*) AS c FROM timesheets t "
#         "JOIN users u ON u.id=t.user_id "
#         "WHERE t.date=? AND t.status='active' AND t.clock_in IS NOT NULL AND t.clock_out IS NULL "
#         "AND u.role IN ('employee','manager')",
#         (today,), fetchone=True
#     )["c"]
#
#     # On break right now
#     on_break = query(
#         "SELECT COUNT(DISTINCT b.timesheet_id) AS c FROM breaks b "
#         "JOIN timesheets t ON t.id=b.timesheet_id "
#         "JOIN users u ON u.id=t.user_id "
#         "WHERE t.date=? AND b.break_out IS NULL "
#         "AND u.role IN ('employee','manager')",
#         (today,), fetchone=True
#     )["c"]
#
#     # Average hours this month (completed timesheets)
#     today_dt = datetime.date.today()
#     prefix   = "{}-{:02d}-%".format(today_dt.year, today_dt.month)
#     rows     = query(
#         "SELECT t.id, t.clock_in, t.clock_out FROM timesheets t "
#         "JOIN users u ON u.id=t.user_id "
#         "WHERE t.date LIKE ? AND t.clock_out IS NOT NULL "
#         "AND u.role IN ('employee','manager')",
#         (prefix,), fetchall=True
#     )
#     avg_hrs = 0.0
#     if rows:
#         total_s = sum(worked_seconds(r, include_active_break=False) for r in rows)
#         avg_hrs = round(total_s / len(rows) / 3600, 1)
#
#     return ok({
#         "total_employees":  total_emp,
#         "clocked_in_today": clocked_in,
#         "on_break":         on_break,
#         "avg_hours_month":  avg_hrs,
#     })
#
#
# @admin_bp.route("/users", methods=["GET"])
# @require_role("admin", "manager")
# def list_users():
#     users = query(
#         "SELECT id,username,email,full_name,role,department,shift_start,shift_end,is_active,created_at,photo "
#         "FROM users ORDER BY role, full_name",
#         fetchall=True
#     )
#     return ok({"users": [safe_user(u) for u in users]})
#
#
# @admin_bp.route("/users", methods=["POST"])
# @require_role("admin")
# def create_user():
#     data = request.get_json(silent=True) or {}
#     for field in ("username", "email", "password", "full_name"):
#         if not str(data.get(field, "")).strip():
#             return err("'{}' is required".format(field))
#     role = data.get("role", "employee")
#     if role not in ROLES:
#         return err("Invalid role")
#     if len(data["password"]) < 8:
#         return err("Password must be at least 8 characters")
#     username = data["username"].strip().lower()
#     email    = data["email"].strip().lower()
#     if query("SELECT id FROM users WHERE username=?", (username,), fetchone=True):
#         return err("Username already taken")
#     if query("SELECT id FROM users WHERE email=?", (email,), fetchone=True):
#         return err("Email already registered")
#     pw_hash = bcrypt.generate_password_hash(data["password"]).decode()
#     uid = execute_lastid(
#         "INSERT INTO users (username,email,password_hash,full_name,role,department,shift_start,shift_end) "
#         "VALUES (?,?,?,?,?,?,?,?)",
#         (username, email, pw_hash, data["full_name"].strip(),
#          role, data.get("department", "").strip(),
#          data.get("shift_start", "09:00"), data.get("shift_end", "18:00"))
#     )
#     user = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
#     return ok({"user": safe_user(user)}, "User created", 201)
#
#
# @admin_bp.route("/users/<int:uid>", methods=["PUT"])
# @require_role("admin")
# def update_user(uid):
#     data   = request.get_json(silent=True) or {}
#     fields = []
#     values = []
#     for col in ("full_name", "email", "department", "shift_start", "shift_end"):
#         if col in data:
#             fields.append("{}=?".format(col))
#             values.append(data[col])
#     if "is_active" in data:
#         fields.append("is_active=?")
#         values.append(1 if data["is_active"] else 0)
#     if data.get("password"):
#         if len(data["password"]) < 8:
#             return err("Password must be at least 8 characters")
#         fields.append("password_hash=?")
#         values.append(bcrypt.generate_password_hash(data["password"]).decode())
#     if not fields:
#         return err("Nothing to update")
#     fields.append("updated_at=datetime('now')")
#     values.append(uid)
#     execute("UPDATE users SET {} WHERE id=?".format(", ".join(fields)), values)
#     updated = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
#     return ok({"user": safe_user(updated)}, "User updated")
#
#
# @admin_bp.route("/users/<int:uid>/role", methods=["PATCH"])
# @require_role("admin")
# def change_role(uid):
#     caller = get_current_user()
#     data   = request.get_json(silent=True) or {}
#     role   = data.get("role", "")
#     if role not in ROLES:
#         return err("Invalid role")
#     if caller["id"] == uid and role != "admin":
#         return err("Cannot demote your own admin account")
#     execute("UPDATE users SET role=?, updated_at=datetime('now') WHERE id=?", (role, uid))
#     updated = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
#     return ok({"user": safe_user(updated)}, "Role updated")
#
#
# @admin_bp.route("/users/<int:uid>", methods=["DELETE"])
# @require_role("admin")
# def delete_user(uid):
#     caller = get_current_user()
#     if caller["id"] == uid:
#         return err("Cannot delete your own account")
#     target = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
#     if not target:
#         return err("User not found", 404)
#     try:
#         # Manually cascade delete all child records first
#         execute("DELETE FROM refresh_tokens WHERE user_id=?", (uid,))
#         execute("DELETE FROM otps WHERE email=(SELECT email FROM users WHERE id=?)", (uid,))
#         # Delete breaks for this user's timesheets
#         execute("DELETE FROM breaks WHERE timesheet_id IN (SELECT id FROM timesheets WHERE user_id=?)", (uid,))
#         execute("DELETE FROM timesheets WHERE user_id=?", (uid,))
#         execute("DELETE FROM spreadsheets WHERE user_id=?", (uid,))
#         execute("DELETE FROM shared_sheet_rows WHERE user_id=?", (uid,))
#         execute("DELETE FROM users WHERE id=?", (uid,))
#         return ok(message="User deleted successfully")
#     except Exception as e:
#         return err("Delete failed: " + str(e), 500)
#
#
# @admin_bp.route("/timesheets", methods=["GET"])
# @require_role("admin", "manager")
# def all_timesheets():
#     year   = request.args.get("year",  datetime.date.today().year,  type=int)
#     month  = request.args.get("month", datetime.date.today().month, type=int)
#     emp_id = request.args.get("emp_id", None, type=int)
#     prefix = "{}-{:02d}-%".format(year, month)
#     sql    = ("SELECT t.*, u.full_name, u.department FROM timesheets t "
#               "JOIN users u ON u.id=t.user_id WHERE t.date LIKE ?")
#     params = [prefix]
#     if emp_id:
#         sql += " AND t.user_id=?"
#         params.append(emp_id)
#     sql += " ORDER BY t.date DESC, t.clock_in DESC"
#     rows = query(sql, params, fetchall=True)
#     return ok({"timesheets": [serialize_ts(r) for r in rows]})
#
#
# @admin_bp.route("/productivity", methods=["GET"])
# @require_role("admin", "manager")
# def productivity():
#     months_back = request.args.get("months", 6, type=int)
#     today       = datetime.date.today()
#     labels      = []
#     month_list  = []
#
#     for i in range(months_back - 1, -1, -1):
#         d = today.replace(day=1)
#         for _ in range(i):
#             prev = d - datetime.timedelta(days=1)
#             d    = prev.replace(day=1)
#         labels.append("{}/{:02d}".format(d.year, d.month))
#         month_list.append((d.year, d.month))
#
#     # Include employees AND managers in chart
#     employees = query(
#         "SELECT id, full_name, role FROM users "
#         "WHERE role IN ('employee','manager') AND is_active=1 ORDER BY full_name",
#         fetchall=True
#     )
#
#     result = []
#     for emp in employees:
#         monthly = []
#         for (yr, mo) in month_list:
#             prefix = "{}-{:02d}-%".format(yr, mo)
#             rows   = query(
#                 "SELECT id, clock_in, clock_out FROM timesheets "
#                 "WHERE user_id=? AND date LIKE ? AND clock_out IS NOT NULL",
#                 (emp["id"], prefix), fetchall=True
#             )
#             total = sum(worked_seconds(r, include_active_break=False) for r in rows)
#             monthly.append(round(total / 3600, 2))
#         result.append({
#             "id":            emp["id"],
#             "name":          emp["full_name"],
#             "role":          emp["role"],
#             "monthly_hours": monthly
#         })
#
#     return ok({"labels": labels, "data": result})
#
#
# @admin_bp.route("/export", methods=["POST"])
# @require_role("admin", "manager")
# def export_report():
#     data   = request.get_json(silent=True) or {}
#     emp_id = data.get("emp_id")          # None = all users
#     year   = int(data.get("year",  datetime.date.today().year))
#     month  = int(data.get("month", datetime.date.today().month))
#     prefix = "{}-{:02d}-%".format(year, month)
#
#     buf    = io.StringIO()
#     writer = csv.writer(buf)
#
#     if emp_id:
#         # Single user export
#         emp = query("SELECT * FROM users WHERE id=?", (emp_id,), fetchone=True)
#         if not emp:
#             return err("User not found", 404)
#         rows = query(
#             "SELECT * FROM timesheets WHERE user_id=? AND date LIKE ? ORDER BY date",
#             (emp_id, prefix), fetchall=True
#         )
#         writer.writerow(["Employee", emp["full_name"]])
#         writer.writerow(["Role",     emp["role"]])
#         writer.writerow(["Period",   "{}/{:02d}".format(year, month)])
#         writer.writerow([])
#         writer.writerow(["Date", "Clock In", "Clock Out", "Break", "Worked Hrs", "Decimal Hrs"])
#         total = 0.0
#         for r in rows:
#             s = serialize_ts(r)
#             writer.writerow([r["date"], s["clock_in"] or "-", s["clock_out"] or "-",
#                              s["break_display"], s["worked_display"], s["worked_decimal"]])
#             total += s["worked_seconds"]
#         writer.writerow([])
#         writer.writerow(["TOTAL", "", "", "", secs_to_hms(total), secs_to_decimal(total)])
#         filename = "timesheet_{}_{}_{}.csv".format(
#             emp["full_name"].replace(" ", "_"), year, "{:02d}".format(month)
#         )
#         employee_label = emp["full_name"]
#
#     else:
#         # All users export — include all active employees AND managers
#         users = query(
#             "SELECT * FROM users WHERE role IN ('employee','manager') ORDER BY role, full_name",
#             fetchall=True
#         )
#         writer.writerow(["All Users Timesheet Report"])
#         writer.writerow(["Period", "{}/{:02d}".format(year, month)])
#         writer.writerow([])
#         writer.writerow(["Employee", "Role", "Department", "Date", "Clock In", "Clock Out",
#                          "Break", "Worked Hrs", "Decimal Hrs"])
#         grand_total = 0.0
#         for emp in users:
#             rows = query(
#                 "SELECT * FROM timesheets WHERE user_id=? AND date LIKE ? ORDER BY date",
#                 (emp["id"], prefix), fetchall=True
#             )
#             for r in rows:
#                 s = serialize_ts(r)
#                 writer.writerow([
#                     emp["full_name"], emp["role"], emp.get("department", ""),
#                     r["date"], s["clock_in"] or "-", s["clock_out"] or "-",
#                     s["break_display"], s["worked_display"], s["worked_decimal"]
#                 ])
#                 grand_total += s["worked_seconds"]
#         writer.writerow([])
#         writer.writerow(["GRAND TOTAL", "", "", "", "", "", "",
#                          secs_to_hms(grand_total), secs_to_decimal(grand_total)])
#         filename  = "all_users_timesheet_{}_{}.csv".format(year, "{:02d}".format(month))
#         employee_label = "All Users"
#         total = grand_total
#
#     csv_b64 = base64.b64encode(buf.getvalue().encode()).decode()
#     return ok({
#         "employee":      employee_label,
#         "total_display": secs_to_hms(total),
#         "csv_b64":       csv_b64,
#         "filename":      filename,
#     })
#
# # ── Holidays ──────────────────────────────────────────────────────────────────
#
# @admin_bp.route("/holidays", methods=["GET"])
# @require_role("admin", "manager", "employee")
# def list_holidays():
#     from app.utils import require_auth
#     year  = request.args.get("year",  datetime.date.today().year,  type=int)
#     month = request.args.get("month", None, type=int)
#     if month:
#         prefix = "{}-{:02d}-%".format(year, month)
#         rows = query("SELECT * FROM holidays WHERE date LIKE ? ORDER BY date", (prefix,), fetchall=True)
#     else:
#         rows = query("SELECT * FROM holidays WHERE date LIKE ? ORDER BY date", ("{}-%".format(year),), fetchall=True)
#     return ok({"holidays": rows or []})
#
#
# @admin_bp.route("/holidays/today", methods=["GET"])
# def check_today_holiday():
#     today = datetime.date.today().isoformat()
#     h = query("SELECT * FROM holidays WHERE date=?", (today,), fetchone=True)
#     return ok({"holiday": h, "is_holiday": h is not None})
#
#
# @admin_bp.route("/holidays", methods=["POST"])
# @require_role("admin")
# def add_holiday():
#     caller = get_current_user()
#     data   = request.get_json(silent=True) or {}
#     date   = str(data.get("date", "")).strip()
#     name   = str(data.get("name", "")).strip()
#     desc   = str(data.get("description", "")).strip()
#     if not date or not name:
#         return err("Date and name are required")
#     # Validate date format
#     try:
#         datetime.date.fromisoformat(date)
#     except ValueError:
#         return err("Invalid date format. Use YYYY-MM-DD")
#     if query("SELECT id FROM holidays WHERE date=?", (date,), fetchone=True):
#         return err("A holiday already exists on this date")
#     hid = execute_lastid(
#         "INSERT INTO holidays (date, name, description, created_by) VALUES (?,?,?,?)",
#         (date, name, desc, caller["id"])
#     )
#     h = query("SELECT * FROM holidays WHERE id=?", (hid,), fetchone=True)
#     return ok({"holiday": h}, "Holiday added!", 201)
#
#
# @admin_bp.route("/holidays/<int:hid>", methods=["DELETE"])
# @require_role("admin")
# def delete_holiday(hid):
#     h = query("SELECT * FROM holidays WHERE id=?", (hid,), fetchone=True)
#     if not h:
#         return err("Holiday not found", 404)
#     execute("DELETE FROM holidays WHERE id=?", (hid,))
#     return ok(message="Holiday deleted")
#
#
# # ── Live attendance detail ─────────────────────────────────────────────────────
#
# @admin_bp.route("/clocked-in", methods=["GET"])
# @require_role("admin", "manager")
# def clocked_in_list():
#     """Users currently clocked in (not on break)."""
#     today = datetime.date.today().isoformat()
#     rows  = query(
#         "SELECT u.id, u.full_name, u.department, u.timezone as user_tz, "
#         "t.id as ts_id, t.clock_in, t.timezone as ts_tz "
#         "FROM timesheets t JOIN users u ON u.id=t.user_id "
#         "WHERE t.date=? AND t.status='active' AND t.clock_in IS NOT NULL AND t.clock_out IS NULL "
#         "AND u.role IN ('employee','manager') "
#         "AND t.id NOT IN (SELECT timesheet_id FROM breaks WHERE break_out IS NULL) "
#         "ORDER BY t.clock_in",
#         (today,), fetchall=True
#     )
#     return ok({"users": rows or []})
#
#
# @admin_bp.route("/on-break", methods=["GET"])
# @require_role("admin", "manager")
# def on_break_list():
#     """Users currently on break."""
#     today = datetime.date.today().isoformat()
#     rows  = query(
#         "SELECT u.id, u.full_name, u.department, u.timezone as user_tz, "
#         "t.id as ts_id, t.clock_in, t.timezone as ts_tz, b.break_in "
#         "FROM breaks b "
#         "JOIN timesheets t ON t.id=b.timesheet_id "
#         "JOIN users u ON u.id=t.user_id "
#         "WHERE t.date=? AND b.break_out IS NULL "
#         "AND u.role IN ('employee','manager') "
#         "ORDER BY b.break_in",
#         (today,), fetchall=True
#     )
#     return ok({"users": rows or []})
#
#
# @admin_bp.route("/auto-clockout", methods=["POST"])
# @require_role("admin", "manager")
# def auto_clockout():
#     """Force clock-out a specific timesheet at 23:59 of its timezone date."""
#     data  = request.get_json(silent=True) or {}
#     ts_id = data.get("ts_id")
#     if not ts_id:
#         return err("ts_id required")
#     ts = query("SELECT * FROM timesheets WHERE id=?", (ts_id,), fetchone=True)
#     if not ts:
#         return err("Timesheet not found", 404)
#     if ts["clock_out"]:
#         return err("Already clocked out")
#
#     # Close any open break first
#     open_brk = query(
#         "SELECT id FROM breaks WHERE timesheet_id=? AND break_out IS NULL",
#         (ts_id,), fetchone=True
#     )
#     clock_out_time = ts["date"] + " 23:59:00"
#     if open_brk:
#         execute("UPDATE breaks SET break_out=? WHERE id=?", (clock_out_time, open_brk["id"]))
#
#     execute(
#         "UPDATE timesheets SET clock_out=?, status='completed' WHERE id=?",
#         (clock_out_time, ts_id)
#     )
#     return ok(message="Auto clocked out at 23:59")
#
#
# # ── Photo upload ───────────────────────────────────────────────────────────────
#
# @admin_bp.route("/users/<int:uid>/photo", methods=["POST"])
# @require_role("admin")
# def upload_photo(uid):
#     import base64
#     data   = request.get_json(silent=True) or {}
#     photo  = data.get("photo_b64", "").strip()
#     if not photo:
#         return err("No photo data provided")
#     # Validate it's a proper base64 image (jpeg or png)
#     if not (photo.startswith("data:image/jpeg") or photo.startswith("data:image/png")
#             or photo.startswith("data:image/webp") or photo.startswith("data:image/gif")):
#         return err("Invalid image format. Use JPEG or PNG.")
#     # Limit size to ~500KB base64
#     if len(photo) > 700000:
#         return err("Image too large. Please use an image under 500KB.")
#     execute("UPDATE users SET photo=?, updated_at=datetime('now') WHERE id=?", (photo, uid))
#     return ok(message="Photo updated!")
#
#
# @admin_bp.route("/users/<int:uid>/photo", methods=["DELETE"])
# @require_role("admin")
# def delete_photo(uid):
#     execute("UPDATE users SET photo=NULL, updated_at=datetime('now') WHERE id=?", (uid,))
#     return ok(message="Photo removed")
#
#
# # ── Shifts ─────────────────────────────────────────────────────────────────────
#
# @admin_bp.route("/shifts", methods=["GET"])
# @require_role("admin", "manager")
# def list_shifts():
#     rows = query("SELECT * FROM shifts ORDER BY name", fetchall=True)
#     return ok({"shifts": rows or []})
#
#
# @admin_bp.route("/shifts", methods=["POST"])
# @require_role("admin")
# def create_shift():
#     data  = request.get_json(silent=True) or {}
#     name  = str(data.get("name",  "")).strip()
#     start = str(data.get("start", "")).strip()
#     end   = str(data.get("end",   "")).strip()
#     desc  = str(data.get("description", "")).strip()
#     if not name or not start or not end:
#         return err("Name, start and end time are required")
#     if query("SELECT id FROM shifts WHERE name=?", (name,), fetchone=True):
#         return err("Shift name already exists")
#     sid = execute_lastid(
#         "INSERT INTO shifts (name, start_time, end_time, description) VALUES (?,?,?,?)",
#         (name, start, end, desc)
#     )
#     shift = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
#     return ok({"shift": shift}, "Shift created!", 201)
#
#
# @admin_bp.route("/shifts/<int:sid>", methods=["PUT"])
# @require_role("admin")
# def update_shift(sid):
#     data   = request.get_json(silent=True) or {}
#     fields = []
#     values = []
#     for col in ("name", "start_time", "end_time", "description"):
#         if col in data:
#             fields.append("{}=?".format(col))
#             values.append(data[col])
#     if not fields:
#         return err("Nothing to update")
#     values.append(sid)
#     execute("UPDATE shifts SET {} WHERE id=?".format(", ".join(fields)), values)
#     updated = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
#     return ok({"shift": updated}, "Shift updated")
#
#
# @admin_bp.route("/shifts/<int:sid>", methods=["DELETE"])
# @require_role("admin")
# def delete_shift(sid):
#     shift = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
#     if not shift:
#         return err("Shift not found", 404)
#     execute("DELETE FROM shifts WHERE id=?", (sid,))
#     return ok(message="Shift deleted")
#
#
# @admin_bp.route("/shifts/<int:sid>/assign", methods=["POST"])
# @require_role("admin")
# def assign_shift(sid):
#     """Assign shift to one or more users."""
#     data   = request.get_json(silent=True) or {}
#     uids   = data.get("user_ids", [])
#     shift  = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
#     if not shift:
#         return err("Shift not found", 404)
#     for uid in uids:
#         execute(
#             "UPDATE users SET shift_start=?, shift_end=?, updated_at=datetime('now') WHERE id=?",
#             (shift["start_time"], shift["end_time"], uid)
#         )
#     return ok(message="Shift assigned to {} user(s)".format(len(uids)))

import csv
import io
import base64
import datetime
from flask import Blueprint, request
from flask_jwt_extended import get_current_user
from flask_bcrypt import Bcrypt
from app.database import query, execute, execute_lastid
from app.utils import ok, err, require_role, secs_to_hms, secs_to_decimal
from app.api.timesheets import serialize_ts, break_seconds, worked_seconds

admin_bp = Blueprint("admin", __name__)
bcrypt   = Bcrypt()
ROLES    = ("admin", "manager", "employee")


def safe_user(u):
    if not u:
        return None
    return {
        "id":          u["id"],
        "username":    u["username"],
        "email":       u["email"],
        "full_name":   u["full_name"],
        "role":        u["role"],
        "department":  u["department"],
        "shift_start": u["shift_start"],
        "shift_end":   u["shift_end"],
        "is_active":   bool(u["is_active"]),
        "created_at":  u["created_at"],
        "photo":       u.get("photo", None)
    }


@admin_bp.route("/overview", methods=["GET"])
@require_role("admin", "manager")
def overview():
    today = datetime.date.today().isoformat()

    # Total active employees + managers (everyone except admin)
    total_emp = query(
        "SELECT COUNT(*) AS c FROM users WHERE role IN ('employee','manager') AND is_active=1",
        fetchone=True
    )["c"]

    # Clocked in today (active timesheet, not clocked out yet)
    clocked_in = query(
        "SELECT COUNT(*) AS c FROM timesheets t "
        "JOIN users u ON u.id=t.user_id "
        "WHERE t.date=? AND t.status='active' AND t.clock_in IS NOT NULL AND t.clock_out IS NULL "
        "AND u.role IN ('employee','manager')",
        (today,), fetchone=True
    )["c"]

    # On break right now
    on_break = query(
        "SELECT COUNT(DISTINCT b.timesheet_id) AS c FROM breaks b "
        "JOIN timesheets t ON t.id=b.timesheet_id "
        "JOIN users u ON u.id=t.user_id "
        "WHERE t.date=? AND b.break_out IS NULL "
        "AND u.role IN ('employee','manager')",
        (today,), fetchone=True
    )["c"]

    # Average hours this month (completed timesheets)
    today_dt = datetime.date.today()
    prefix   = "{}-{:02d}-%".format(today_dt.year, today_dt.month)
    rows     = query(
        "SELECT t.id, t.clock_in, t.clock_out FROM timesheets t "
        "JOIN users u ON u.id=t.user_id "
        "WHERE t.date LIKE ? AND t.clock_out IS NOT NULL "
        "AND u.role IN ('employee','manager')",
        (prefix,), fetchall=True
    )
    avg_hrs = 0.0
    if rows:
        total_s = sum(worked_seconds(r, include_active_break=False) for r in rows)
        avg_hrs = round(total_s / len(rows) / 3600, 1)

    return ok({
        "total_employees":  total_emp,
        "clocked_in_today": clocked_in,
        "on_break":         on_break,
        "avg_hours_month":  avg_hrs,
    })


@admin_bp.route("/users", methods=["GET"])
@require_role("admin", "manager")
def list_users():
    users = query(
        "SELECT id,username,email,full_name,role,department,shift_start,shift_end,is_active,created_at,photo "
        "FROM users ORDER BY role, full_name",
        fetchall=True
    )
    return ok({"users": [safe_user(u) for u in users]})


@admin_bp.route("/users", methods=["POST"])
@require_role("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    for field in ("username", "email", "password", "full_name"):
        if not str(data.get(field, "")).strip():
            return err("'{}' is required".format(field))
    role = data.get("role", "employee")
    if role not in ROLES:
        return err("The selected role is not valid")
    if len(data["password"]) < 8:
        return err("Password must be at least 8 characters")
    username = data["username"].strip().lower()
    email    = data["email"].strip().lower()
    if query("SELECT id FROM users WHERE username=?", (username,), fetchone=True):
        return err("This username is already taken. Please choose a different one")
    if query("SELECT id FROM users WHERE email=?", (email,), fetchone=True):
        return err("Email already registered")
    pw_hash = bcrypt.generate_password_hash(data["password"]).decode()
    uid = execute_lastid(
        "INSERT INTO users (username,email,password_hash,full_name,role,department,shift_start,shift_end) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (username, email, pw_hash, data["full_name"].strip(),
         role, data.get("department", "").strip(),
         data.get("shift_start", "09:00"), data.get("shift_end", "18:00"))
    )
    user = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    return ok({"user": safe_user(user)}, "User created", 201)


@admin_bp.route("/users/<int:uid>", methods=["PUT"])
@require_role("admin")
def update_user(uid):
    data   = request.get_json(silent=True) or {}
    fields = []
    values = []
    for col in ("full_name", "email", "department", "shift_start", "shift_end"):
        if col in data:
            fields.append("{}=?".format(col))
            values.append(data[col])
    if "is_active" in data:
        fields.append("is_active=?")
        values.append(1 if data["is_active"] else 0)
    if data.get("password"):
        if len(data["password"]) < 8:
            return err("Password must be at least 8 characters")
        fields.append("password_hash=?")
        values.append(bcrypt.generate_password_hash(data["password"]).decode())
    if not fields:
        return err("No changes were detected")
    fields.append("updated_at=datetime('now')")
    values.append(uid)
    execute("UPDATE users SET {} WHERE id=?".format(", ".join(fields)), values)
    updated = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    return ok({"user": safe_user(updated)}, "User updated")


@admin_bp.route("/users/<int:uid>/role", methods=["PATCH"])
@require_role("admin")
def change_role(uid):
    caller = get_current_user()
    data   = request.get_json(silent=True) or {}
    role   = data.get("role", "")
    if role not in ROLES:
        return err("The selected role is not valid")
    if caller["id"] == uid and role != "admin":
        return err("You cannot change your own admin role")
    execute("UPDATE users SET role=?, updated_at=datetime('now') WHERE id=?", (role, uid))
    updated = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    return ok({"user": safe_user(updated)}, "Role updated")


@admin_bp.route("/users/<int:uid>", methods=["DELETE"])
@require_role("admin")
def delete_user(uid):
    caller = get_current_user()
    if caller["id"] == uid:
        return err("You cannot delete your own admin account")
    target = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    if not target:
        return err("This user account could not be found", 404)
    try:
        # Manually cascade delete all child records first
        execute("DELETE FROM refresh_tokens WHERE user_id=?", (uid,))
        execute("DELETE FROM otps WHERE email=(SELECT email FROM users WHERE id=?)", (uid,))
        # Delete breaks for this user's timesheets
        execute("DELETE FROM breaks WHERE timesheet_id IN (SELECT id FROM timesheets WHERE user_id=?)", (uid,))
        execute("DELETE FROM timesheets WHERE user_id=?", (uid,))
        execute("DELETE FROM spreadsheets WHERE user_id=?", (uid,))
        execute("DELETE FROM shared_sheet_rows WHERE user_id=?", (uid,))
        execute("DELETE FROM users WHERE id=?", (uid,))
        return ok(message="User deleted successfully")
    except Exception as e:
        return err("Delete failed: " + str(e), 500)


@admin_bp.route("/timesheets", methods=["GET"])
@require_role("admin", "manager")
def all_timesheets():
    year   = request.args.get("year",  datetime.date.today().year,  type=int)
    month  = request.args.get("month", datetime.date.today().month, type=int)
    emp_id = request.args.get("emp_id", None, type=int)
    prefix = "{}-{:02d}-%".format(year, month)
    sql    = ("SELECT t.*, u.full_name, u.department FROM timesheets t "
              "JOIN users u ON u.id=t.user_id WHERE t.date LIKE ?")
    params = [prefix]
    if emp_id:
        sql += " AND t.user_id=?"
        params.append(emp_id)
    sql += " ORDER BY t.date DESC, t.clock_in DESC"
    rows = query(sql, params, fetchall=True)
    return ok({"timesheets": [serialize_ts(r) for r in rows]})


@admin_bp.route("/productivity", methods=["GET"])
@require_role("admin", "manager")
def productivity():
    months_back = request.args.get("months", 6, type=int)
    today       = datetime.date.today()
    labels      = []
    month_list  = []

    for i in range(months_back - 1, -1, -1):
        d = today.replace(day=1)
        for _ in range(i):
            prev = d - datetime.timedelta(days=1)
            d    = prev.replace(day=1)
        labels.append("{}/{:02d}".format(d.year, d.month))
        month_list.append((d.year, d.month))

    # Include employees AND managers in chart
    employees = query(
        "SELECT id, full_name, role FROM users "
        "WHERE role IN ('employee','manager') AND is_active=1 ORDER BY full_name",
        fetchall=True
    )

    result = []
    for emp in employees:
        monthly = []
        for (yr, mo) in month_list:
            prefix = "{}-{:02d}-%".format(yr, mo)
            rows   = query(
                "SELECT id, clock_in, clock_out FROM timesheets "
                "WHERE user_id=? AND date LIKE ? AND clock_out IS NOT NULL",
                (emp["id"], prefix), fetchall=True
            )
            total = sum(worked_seconds(r, include_active_break=False) for r in rows)
            monthly.append(round(total / 3600, 2))
        result.append({
            "id":            emp["id"],
            "name":          emp["full_name"],
            "role":          emp["role"],
            "monthly_hours": monthly
        })

    return ok({"labels": labels, "data": result})


@admin_bp.route("/export", methods=["POST"])
@require_role("admin", "manager")
def export_report():
    data   = request.get_json(silent=True) or {}
    emp_id = data.get("emp_id")          # None = all users
    year   = int(data.get("year",  datetime.date.today().year))
    month  = int(data.get("month", datetime.date.today().month))
    prefix = "{}-{:02d}-%".format(year, month)

    buf    = io.StringIO()
    writer = csv.writer(buf)

    if emp_id:
        # Single user export
        emp = query("SELECT * FROM users WHERE id=?", (emp_id,), fetchone=True)
        if not emp:
            return err("This user account could not be found", 404)
        rows = query(
            "SELECT * FROM timesheets WHERE user_id=? AND date LIKE ? ORDER BY date",
            (emp_id, prefix), fetchall=True
        )
        writer.writerow(["Employee", emp["full_name"]])
        writer.writerow(["Role",     emp["role"]])
        writer.writerow(["Period",   "{}/{:02d}".format(year, month)])
        writer.writerow([])
        writer.writerow(["Date", "Clock In", "Clock Out", "Break", "Worked Hrs", "Decimal Hrs"])
        total = 0.0
        for r in rows:
            s = serialize_ts(r)
            writer.writerow([r["date"], s["clock_in"] or "-", s["clock_out"] or "-",
                             s["break_display"], s["worked_display"], s["worked_decimal"]])
            total += s["worked_seconds"]
        writer.writerow([])
        writer.writerow(["TOTAL", "", "", "", secs_to_hms(total), secs_to_decimal(total)])
        filename = "timesheet_{}_{}_{}.csv".format(
            emp["full_name"].replace(" ", "_"), year, "{:02d}".format(month)
        )
        employee_label = emp["full_name"]

    else:
        # All users export — include all active employees AND managers
        users = query(
            "SELECT * FROM users WHERE role IN ('employee','manager') ORDER BY role, full_name",
            fetchall=True
        )
        writer.writerow(["All Users Timesheet Report"])
        writer.writerow(["Period", "{}/{:02d}".format(year, month)])
        writer.writerow([])
        writer.writerow(["Employee", "Role", "Department", "Date", "Clock In", "Clock Out",
                         "Break", "Worked Hrs", "Decimal Hrs"])
        grand_total = 0.0
        for emp in users:
            rows = query(
                "SELECT * FROM timesheets WHERE user_id=? AND date LIKE ? ORDER BY date",
                (emp["id"], prefix), fetchall=True
            )
            for r in rows:
                s = serialize_ts(r)
                writer.writerow([
                    emp["full_name"], emp["role"], emp.get("department", ""),
                    r["date"], s["clock_in"] or "-", s["clock_out"] or "-",
                    s["break_display"], s["worked_display"], s["worked_decimal"]
                ])
                grand_total += s["worked_seconds"]
        writer.writerow([])
        writer.writerow(["GRAND TOTAL", "", "", "", "", "", "",
                         secs_to_hms(grand_total), secs_to_decimal(grand_total)])
        filename  = "all_users_timesheet_{}_{}.csv".format(year, "{:02d}".format(month))
        employee_label = "All Users"
        total = grand_total

    csv_b64 = base64.b64encode(buf.getvalue().encode()).decode()
    return ok({
        "employee":      employee_label,
        "total_display": secs_to_hms(total),
        "csv_b64":       csv_b64,
        "filename":      filename,
    })

# ── Holidays ──────────────────────────────────────────────────────────────────

@admin_bp.route("/holidays", methods=["GET"])
@require_role("admin", "manager", "employee")
def list_holidays():
    from app.utils import require_auth
    year  = request.args.get("year",  datetime.date.today().year,  type=int)
    month = request.args.get("month", None, type=int)
    if month:
        prefix = "{}-{:02d}-%".format(year, month)
        rows = query("SELECT * FROM holidays WHERE date LIKE ? ORDER BY date", (prefix,), fetchall=True)
    else:
        rows = query("SELECT * FROM holidays WHERE date LIKE ? ORDER BY date", ("{}-%".format(year),), fetchall=True)
    return ok({"holidays": rows or []})


@admin_bp.route("/holidays/today", methods=["GET"])
def check_today_holiday():
    today = datetime.date.today().isoformat()
    h = query("SELECT * FROM holidays WHERE date=?", (today,), fetchone=True)
    return ok({"holiday": h, "is_holiday": h is not None})


@admin_bp.route("/holidays", methods=["POST"])
@require_role("admin")
def add_holiday():
    caller = get_current_user()
    data   = request.get_json(silent=True) or {}
    date   = str(data.get("date", "")).strip()
    name   = str(data.get("name", "")).strip()
    desc   = str(data.get("description", "")).strip()
    if not date or not name:
        return err("Date and name are required")
    # Validate date format
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return err("Invalid date format. Use YYYY-MM-DD")
    if query("SELECT id FROM holidays WHERE date=?", (date,), fetchone=True):
        return err("A holiday is already set for this date")
    hid = execute_lastid(
        "INSERT INTO holidays (date, name, description, created_by) VALUES (?,?,?,?)",
        (date, name, desc, caller["id"])
    )
    h = query("SELECT * FROM holidays WHERE id=?", (hid,), fetchone=True)
    return ok({"holiday": h}, "Holiday added!", 201)


@admin_bp.route("/holidays/<int:hid>", methods=["DELETE"])
@require_role("admin")
def delete_holiday(hid):
    h = query("SELECT * FROM holidays WHERE id=?", (hid,), fetchone=True)
    if not h:
        return err("This holiday could not be found", 404)
    execute("DELETE FROM holidays WHERE id=?", (hid,))
    return ok(message="Holiday deleted")


# ── Live attendance detail ─────────────────────────────────────────────────────

@admin_bp.route("/clocked-in", methods=["GET"])
@require_role("admin", "manager")
def clocked_in_list():
    """Users currently clocked in (not on break)."""
    today = datetime.date.today().isoformat()
    rows  = query(
        "SELECT u.id, u.full_name, u.department, u.timezone as user_tz, "
        "t.id as ts_id, t.clock_in, t.timezone as ts_tz "
        "FROM timesheets t JOIN users u ON u.id=t.user_id "
        "WHERE t.date=? AND t.status='active' AND t.clock_in IS NOT NULL AND t.clock_out IS NULL "
        "AND u.role IN ('employee','manager') "
        "AND t.id NOT IN (SELECT timesheet_id FROM breaks WHERE break_out IS NULL) "
        "ORDER BY t.clock_in",
        (today,), fetchall=True
    )
    return ok({"users": rows or []})


@admin_bp.route("/on-break", methods=["GET"])
@require_role("admin", "manager")
def on_break_list():
    """Users currently on break."""
    today = datetime.date.today().isoformat()
    rows  = query(
        "SELECT u.id, u.full_name, u.department, u.timezone as user_tz, "
        "t.id as ts_id, t.clock_in, t.timezone as ts_tz, b.break_in "
        "FROM breaks b "
        "JOIN timesheets t ON t.id=b.timesheet_id "
        "JOIN users u ON u.id=t.user_id "
        "WHERE t.date=? AND b.break_out IS NULL "
        "AND u.role IN ('employee','manager') "
        "ORDER BY b.break_in",
        (today,), fetchall=True
    )
    return ok({"users": rows or []})


@admin_bp.route("/auto-clockout", methods=["POST"])
@require_role("admin", "manager")
def auto_clockout():
    """Force clock-out a specific timesheet at 23:59 of its timezone date."""
    data  = request.get_json(silent=True) or {}
    ts_id = data.get("ts_id")
    if not ts_id:
        return err("ts_id required")
    ts = query("SELECT * FROM timesheets WHERE id=?", (ts_id,), fetchone=True)
    if not ts:
        return err("Timesheet not found", 404)
    if ts["clock_out"]:
        return err("Already clocked out")

    # Close any open break first
    open_brk = query(
        "SELECT id FROM breaks WHERE timesheet_id=? AND break_out IS NULL",
        (ts_id,), fetchone=True
    )
    clock_out_time = ts["date"] + " 23:59:00"
    if open_brk:
        execute("UPDATE breaks SET break_out=? WHERE id=?", (clock_out_time, open_brk["id"]))

    execute(
        "UPDATE timesheets SET clock_out=?, status='completed' WHERE id=?",
        (clock_out_time, ts_id)
    )
    return ok(message="Auto clocked out at 23:59")


# ── Photo upload ───────────────────────────────────────────────────────────────

@admin_bp.route("/users/<int:uid>/photo", methods=["POST"])
@require_role("admin")
def upload_photo(uid):
    import base64
    data   = request.get_json(silent=True) or {}
    photo  = data.get("photo_b64", "").strip()
    if not photo:
        return err("No photo data provided")
    # Validate it's a proper base64 image (jpeg or png)
    if not (photo.startswith("data:image/jpeg") or photo.startswith("data:image/png")
            or photo.startswith("data:image/webp") or photo.startswith("data:image/gif")):
        return err("Invalid image format. Use JPEG or PNG.")
    # Limit size to ~500KB base64
    if len(photo) > 700000:
        return err("Image too large. Please use an image under 500KB.")
    execute("UPDATE users SET photo=?, updated_at=datetime('now') WHERE id=?", (photo, uid))
    return ok(message="Photo updated!")


@admin_bp.route("/users/<int:uid>/photo", methods=["DELETE"])
@require_role("admin")
def delete_photo(uid):
    execute("UPDATE users SET photo=NULL, updated_at=datetime('now') WHERE id=?", (uid,))
    return ok(message="Photo removed")


# ── Shifts ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/shifts", methods=["GET"])
@require_role("admin", "manager")
def list_shifts():
    rows = query("SELECT * FROM shifts ORDER BY name", fetchall=True)
    return ok({"shifts": rows or []})


@admin_bp.route("/shifts", methods=["POST"])
@require_role("admin")
def create_shift():
    data  = request.get_json(silent=True) or {}
    name  = str(data.get("name",  "")).strip()
    start = str(data.get("start", "")).strip()
    end   = str(data.get("end",   "")).strip()
    desc  = str(data.get("description", "")).strip()
    if not name or not start or not end:
        return err("Name, start and end time are required")
    if query("SELECT id FROM shifts WHERE name=?", (name,), fetchone=True):
        return err("A shift with this name already exists")
    sid = execute_lastid(
        "INSERT INTO shifts (name, start_time, end_time, description) VALUES (?,?,?,?)",
        (name, start, end, desc)
    )
    shift = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
    return ok({"shift": shift}, "Shift created!", 201)


@admin_bp.route("/shifts/<int:sid>", methods=["PUT"])
@require_role("admin")
def update_shift(sid):
    data   = request.get_json(silent=True) or {}
    fields = []
    values = []
    for col in ("name", "start_time", "end_time", "description"):
        if col in data:
            fields.append("{}=?".format(col))
            values.append(data[col])
    if not fields:
        return err("No changes were detected")
    values.append(sid)
    execute("UPDATE shifts SET {} WHERE id=?".format(", ".join(fields)), values)
    updated = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
    return ok({"shift": updated}, "Shift updated")


@admin_bp.route("/shifts/<int:sid>", methods=["DELETE"])
@require_role("admin")
def delete_shift(sid):
    shift = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
    if not shift:
        return err("This shift does not exist", 404)
    execute("DELETE FROM shifts WHERE id=?", (sid,))
    return ok(message="Shift deleted")


@admin_bp.route("/shifts/<int:sid>/assign", methods=["POST"])
@require_role("admin")
def assign_shift(sid):
    """Assign shift to one or more users."""
    data   = request.get_json(silent=True) or {}
    uids   = data.get("user_ids", [])
    shift  = query("SELECT * FROM shifts WHERE id=?", (sid,), fetchone=True)
    if not shift:
        return err("This shift does not exist", 404)
    for uid in uids:
        execute(
            "UPDATE users SET shift_start=?, shift_end=?, updated_at=datetime('now') WHERE id=?",
            (shift["start_time"], shift["end_time"], uid)
        )
    return ok(message="Shift assigned to {} user(s)".format(len(uids)))