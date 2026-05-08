# import os
# import hashlib
# import datetime
# from flask import Blueprint, request, jsonify
# from flask_jwt_extended import (
#     create_access_token, create_refresh_token,
#     set_access_cookies, set_refresh_cookies,
#     unset_jwt_cookies, get_current_user, get_jwt_identity,
#     verify_jwt_in_request
# )
# from flask_bcrypt import Bcrypt
# from app.database import query, execute, execute_lastid
# from app.utils import ok, err, require_auth, now_str
# from app.mailer import create_otp, verify_otp, send_login_otp, send_register_otp, send_forgot_otp
#
# auth_bp = Blueprint("auth", __name__)
# bcrypt  = Bcrypt()
# ROLES   = ("admin", "manager", "employee")
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
#         "department":  u.get("department", ""),
#         "shift_start": u.get("shift_start", "09:00"),
#         "shift_end":   u.get("shift_end",   "18:00"),
#         "timezone":    u.get("timezone",    "IST"),
#         "is_active":   bool(u["is_active"]),
#         "created_at":  u["created_at"],
#         "photo":       u.get("photo", None)
#     }
#
#
# def issue_tokens(user):
#     access_token  = create_access_token(identity=str(user["id"]))
#     refresh_token = create_refresh_token(identity=str(user["id"]))
#     token_hash    = hashlib.sha256(refresh_token.encode()).hexdigest()
#     expires_at    = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
#     execute(
#         "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?,?,?)",
#         (user["id"], token_hash, expires_at)
#     )
#     resp = jsonify({"ok": True, "user": safe_user(user), "access_token": access_token})
#     set_access_cookies(resp, access_token)
#     set_refresh_cookies(resp, refresh_token)
#     return resp
#
#
# @auth_bp.route("/register/send-otp", methods=["POST"])
# def register_send_otp():
#     data      = request.get_json(silent=True) or {}
#     email     = str(data.get("email",     "")).strip().lower()
#     full_name = str(data.get("full_name", "")).strip()
#
#     if not email:
#         return err("Email is required")
#     if not full_name:
#         return err("Full name is required")
#     if query("SELECT id FROM users WHERE email=?", (email,), fetchone=True):
#         return err("Email already registered. Please sign in.")
#
#     otp_code = create_otp(email, "register")
#     if not otp_code:
#         return err("Failed to generate OTP. Please try again.")
#
#     sent = send_register_otp(email, full_name, otp_code)
#     if not sent[0]:
#         return err("Failed to send OTP: " + str(sent[1]), 500)
#
#     return ok(message="OTP sent to {}. Check your inbox.".format(email))
#
#
# @auth_bp.route("/register", methods=["POST"])
# def register():
#     data = request.get_json(silent=True) or {}
#     for field in ("username", "email", "password", "full_name", "otp"):
#         if not str(data.get(field, "")).strip():
#             return err("'{}' is required".format(field))
#
#     username  = data["username"].strip().lower()
#     email     = data["email"].strip().lower()
#     password  = data["password"]
#     full_name = data["full_name"].strip()
#     otp_code  = data["otp"].strip()
#     role      = data.get("role", "employee")
#     dept      = data.get("department", "").strip()
#     shift_s   = data.get("shift_start", "09:00")
#     shift_e   = data.get("shift_end",   "18:00")
#
#     if role not in ROLES:
#         return err("Invalid role")
#     if len(password) < 8:
#         return err("Password must be at least 8 characters")
#     if query("SELECT id FROM users WHERE username=?", (username,), fetchone=True):
#         return err("Username already taken")
#     if query("SELECT id FROM users WHERE email=?", (email,), fetchone=True):
#         return err("Email already registered")
#
#     result = verify_otp(email, otp_code, "register")
#     if not result[0]:
#         return err(result[1])
#
#     count = query("SELECT COUNT(*) AS cnt FROM users", fetchone=True)["cnt"]
#     if count == 0:
#         role = "admin"
#     else:
#         try:
#             verify_jwt_in_request(locations=["headers", "cookies"])
#             caller = get_current_user()
#             if not (caller and caller["role"] == "admin"):
#                 role = "employee"
#         except Exception:
#             role = "employee"
#
#     pw_hash = bcrypt.generate_password_hash(password).decode()
#     uid = execute_lastid(
#         "INSERT INTO users "
#         "(username, email, password_hash, full_name, role, department, shift_start, shift_end) "
#         "VALUES (?,?,?,?,?,?,?,?)",
#         (username, email, pw_hash, full_name, role, dept, shift_s, shift_e)
#     )
#     user = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
#     return ok({"user": safe_user(user)}, "Account created successfully!", 201)
#
#
# @auth_bp.route("/login/send-otp", methods=["POST"])
# def login_send_otp():
#     data       = request.get_json(silent=True) or {}
#     identifier = str(data.get("username", "")).strip().lower()
#     password   = str(data.get("password", ""))
#
#     if not identifier or not password:
#         return err("Username and password required")
#
#     user = query(
#         "SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1",
#         (identifier, identifier), fetchone=True
#     )
#     if not user or not bcrypt.check_password_hash(user["password_hash"], password):
#         return err("Invalid credentials", 401)
#
#     otp_code = create_otp(user["email"], "login")
#     if not otp_code:
#         return err("Failed to generate OTP. Please try again.")
#
#     sent = send_login_otp(user["email"], user["full_name"], otp_code)
#     if not sent[0]:
#         return err("Failed to send OTP: " + str(sent[1]), 500)
#
#     parts      = user["email"].split("@")
#     email_hint = parts[0][:3] + "***@" + parts[1]
#     return ok(
#         {"email_hint": email_hint, "username": identifier},
#         "OTP sent to your registered email."
#     )
#
#
# @auth_bp.route("/login/verify-otp", methods=["POST"])
# def login_verify_otp():
#     data       = request.get_json(silent=True) or {}
#     identifier = str(data.get("username", "")).strip().lower()
#     otp_code   = str(data.get("otp", "")).strip()
#
#     if not identifier or not otp_code:
#         return err("Username and OTP required")
#
#     user = query(
#         "SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1",
#         (identifier, identifier), fetchone=True
#     )
#     if not user:
#         return err("User not found", 401)
#
#     result = verify_otp(user["email"], otp_code, "login")
#     if not result[0]:
#         return err(result[1], 401)
#
#     return issue_tokens(user), 200
#
#
# @auth_bp.route("/forgot-password/send-otp", methods=["POST"])
# def forgot_send_otp():
#     data  = request.get_json(silent=True) or {}
#     email = str(data.get("email", "")).strip().lower()
#
#     if not email:
#         return err("Email is required")
#
#     user = query("SELECT * FROM users WHERE email=? AND is_active=1", (email,), fetchone=True)
#     if not user:
#         return err("No account found with this email address.")
#
#     otp_code = create_otp(email, "forgot")
#     if not otp_code:
#         return err("Failed to generate OTP. Please try again.")
#
#     sent = send_forgot_otp(email, otp_code)
#     if not sent[0]:
#         return err("Failed to send OTP: " + str(sent[1]), 500)
#
#     return ok(message="OTP sent to your registered email.")
#
#
# @auth_bp.route("/forgot-password/reset-with-otp", methods=["POST"])
# def reset_with_otp():
#     data         = request.get_json(silent=True) or {}
#     email        = str(data.get("email",        "")).strip().lower()
#     otp_code     = str(data.get("otp",          "")).strip()
#     new_password = str(data.get("new_password", ""))
#
#     if not email or not otp_code or not new_password:
#         return err("Email, OTP and new password are required")
#     if len(new_password) < 8:
#         return err("Password must be at least 8 characters")
#
#     result = verify_otp(email, otp_code, "forgot")
#     if not result[0]:
#         return err(result[1])
#
#     pw_hash = bcrypt.generate_password_hash(new_password).decode()
#     execute(
#         "UPDATE users SET password_hash=?, updated_at=datetime('now') WHERE email=?",
#         (pw_hash, email)
#     )
#     return ok(message="Password reset successfully! You can now sign in.")
#
#
# @auth_bp.route("/logout", methods=["POST"])
# @require_auth
# def logout():
#     user = get_current_user()
#     if user:
#         execute("DELETE FROM refresh_tokens WHERE user_id=?", (user["id"],))
#     resp = jsonify({"ok": True, "message": "Logged out"})
#     unset_jwt_cookies(resp)
#     return resp, 200
#
#
# @auth_bp.route("/refresh", methods=["POST"])
# def refresh():
#     try:
#         verify_jwt_in_request(refresh=True, locations=["headers", "cookies"])
#     except Exception as e:
#         return err(str(e), 401)
#     uid  = get_jwt_identity()
#     user = query("SELECT * FROM users WHERE id=? AND is_active=1", (uid,), fetchone=True)
#     if not user:
#         return err("User not found", 401)
#     access_token = create_access_token(identity=str(user["id"]))
#     resp = jsonify({"ok": True, "access_token": access_token})
#     set_access_cookies(resp, access_token)
#     return resp, 200
#
#
# @auth_bp.route("/me", methods=["GET"])
# @require_auth
# def me():
#     user = get_current_user()
#     if not user:
#         return err("Not found", 401)
#     return ok({"user": safe_user(user)})
#
#
# @auth_bp.route("/me", methods=["PUT"])
# @require_auth
# def update_profile():
#     user   = get_current_user()
#     data   = request.get_json(silent=True) or {}
#     fields = []
#     values = []
#     for col in ("full_name", "email", "department", "shift_start", "shift_end"):
#         if col in data:
#             fields.append("{}=?".format(col))
#             values.append(str(data[col]).strip())
#     if data.get("password"):
#         if len(data["password"]) < 8:
#             return err("Password must be at least 8 characters")
#         fields.append("password_hash=?")
#         values.append(bcrypt.generate_password_hash(data["password"]).decode())
#     if not fields:
#         return err("Nothing to update")
#     fields.append("updated_at=datetime('now')")
#     values.append(user["id"])
#     execute("UPDATE users SET {} WHERE id=?".format(", ".join(fields)), values)
#     updated = query("SELECT * FROM users WHERE id=?", (user["id"],), fetchone=True)
#     return ok({"user": safe_user(updated)}, "Profile updated")

import os
import hashlib
import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, get_current_user, get_jwt_identity,
    verify_jwt_in_request
)
from flask_bcrypt import Bcrypt
from app.database import query, execute, execute_lastid
from app.utils import ok, err, require_auth, now_str
from app.mailer import create_otp, verify_otp, send_login_otp, send_register_otp, send_forgot_otp

auth_bp = Blueprint("auth", __name__)
bcrypt  = Bcrypt()
ROLES   = ("admin", "manager", "employee")


def safe_user(u):
    if not u:
        return None
    return {
        "id":          u["id"],
        "username":    u["username"],
        "email":       u["email"],
        "full_name":   u["full_name"],
        "role":        u["role"],
        "department":  u.get("department", ""),
        "shift_start": u.get("shift_start", "09:00"),
        "shift_end":   u.get("shift_end",   "18:00"),
        "timezone":    u.get("timezone",    "IST"),
        "is_active":   bool(u["is_active"]),
        "created_at":  u["created_at"],
        "photo":       u.get("photo", None)
    }


def issue_tokens(user):
    access_token  = create_access_token(identity=str(user["id"]))
    refresh_token = create_refresh_token(identity=str(user["id"]))
    token_hash    = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at    = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
    execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?,?,?)",
        (user["id"], token_hash, expires_at)
    )
    resp = jsonify({"ok": True, "user": safe_user(user), "access_token": access_token})
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@auth_bp.route("/register/send-otp", methods=["POST"])
def register_send_otp():
    data      = request.get_json(silent=True) or {}
    email     = str(data.get("email",     "")).strip().lower()
    full_name = str(data.get("full_name", "")).strip()

    if not email:
        return err("Please enter your email address")
    if not full_name:
        return err("Please enter your full name")
    if query("SELECT id FROM users WHERE email=?", (email,), fetchone=True):
        return err("This email is already registered. Please sign in instead")

    otp_code = create_otp(email, "register")
    if not otp_code:
        return err("Failed to generate OTP. Please try again.")

    sent = send_register_otp(email, full_name, otp_code)
    if not sent[0]:
        return err("Failed to send OTP: " + str(sent[1]), 500)

    return ok(message="OTP sent to {}. Check your inbox.".format(email))


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    for field in ("username", "email", "password", "full_name", "otp"):
        if not str(data.get(field, "")).strip():
            return err("'{}' is required".format(field))

    username  = data["username"].strip().lower()
    email     = data["email"].strip().lower()
    password  = data["password"]
    full_name = data["full_name"].strip()
    otp_code  = data["otp"].strip()
    role      = data.get("role", "employee")
    dept      = data.get("department", "").strip()
    shift_s   = data.get("shift_start", "09:00")
    shift_e   = data.get("shift_end",   "18:00")

    if role not in ROLES:
        return err("The selected role is not valid")
    if len(password) < 8:
        return err("Your password must be at least 8 characters long")
    if query("SELECT id FROM users WHERE username=?", (username,), fetchone=True):
        return err("This username is already taken. Please choose a different one")
    if query("SELECT id FROM users WHERE email=?", (email,), fetchone=True):
        return err("This email address is already in use")

    result = verify_otp(email, otp_code, "register")
    if not result[0]:
        return err(result[1])

    count = query("SELECT COUNT(*) AS cnt FROM users", fetchone=True)["cnt"]
    if count == 0:
        role = "admin"
    else:
        try:
            verify_jwt_in_request(locations=["headers", "cookies"])
            caller = get_current_user()
            if not (caller and caller["role"] == "admin"):
                role = "employee"
        except Exception:
            role = "employee"

    pw_hash = bcrypt.generate_password_hash(password).decode()
    uid = execute_lastid(
        "INSERT INTO users "
        "(username, email, password_hash, full_name, role, department, shift_start, shift_end) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (username, email, pw_hash, full_name, role, dept, shift_s, shift_e)
    )
    user = query("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    return ok({"user": safe_user(user)}, "Account created successfully!", 201)


@auth_bp.route("/login/send-otp", methods=["POST"])
def login_send_otp():
    data       = request.get_json(silent=True) or {}
    identifier = str(data.get("username", "")).strip().lower()
    password   = str(data.get("password", ""))

    if not identifier or not password:
        return err("Please enter your username and password")

    user = query(
        "SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1",
        (identifier, identifier), fetchone=True
    )
    if not user or not bcrypt.check_password_hash(user["password_hash"], password):
        return err("Incorrect username or password. Please try again", 401)

    otp_code = create_otp(user["email"], "login")
    if not otp_code:
        return err("Failed to generate OTP. Please try again.")

    sent = send_login_otp(user["email"], user["full_name"], otp_code)
    if not sent[0]:
        return err("Failed to send OTP: " + str(sent[1]), 500)

    parts      = user["email"].split("@")
    email_hint = parts[0][:3] + "***@" + parts[1]
    return ok(
        {"email_hint": email_hint, "username": identifier},
        "OTP sent to your registered email."
    )


@auth_bp.route("/login/verify-otp", methods=["POST"])
def login_verify_otp():
    data       = request.get_json(silent=True) or {}
    identifier = str(data.get("username", "")).strip().lower()
    otp_code   = str(data.get("otp", "")).strip()

    if not identifier or not otp_code:
        return err("Username and OTP required")

    user = query(
        "SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1",
        (identifier, identifier), fetchone=True
    )
    if not user:
        return err("This user account could not be found", 401)

    result = verify_otp(user["email"], otp_code, "login")
    if not result[0]:
        return err(result[1], 401)

    return issue_tokens(user), 200


@auth_bp.route("/forgot-password/send-otp", methods=["POST"])
def forgot_send_otp():
    data  = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email:
        return err("Please enter your email address")

    user = query("SELECT * FROM users WHERE email=? AND is_active=1", (email,), fetchone=True)
    if not user:
        return err("No account was found with that email. Please check and try again")

    otp_code = create_otp(email, "forgot")
    if not otp_code:
        return err("Failed to generate OTP. Please try again.")

    sent = send_forgot_otp(email, otp_code)
    if not sent[0]:
        return err("Failed to send OTP: " + str(sent[1]), 500)

    return ok(message="OTP sent to your registered email.")


@auth_bp.route("/forgot-password/reset-with-otp", methods=["POST"])
def reset_with_otp():
    data         = request.get_json(silent=True) or {}
    email        = str(data.get("email",        "")).strip().lower()
    otp_code     = str(data.get("otp",          "")).strip()
    new_password = str(data.get("new_password", ""))

    if not email or not otp_code or not new_password:
        return err("Email, OTP and new password are required")
    if len(new_password) < 8:
        return err("Your password must be at least 8 characters long")

    result = verify_otp(email, otp_code, "forgot")
    if not result[0]:
        return err(result[1])

    pw_hash = bcrypt.generate_password_hash(new_password).decode()
    execute(
        "UPDATE users SET password_hash=?, updated_at=datetime('now') WHERE email=?",
        (pw_hash, email)
    )
    return ok(message="Password reset successfully! You can now sign in.")


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    user = get_current_user()
    if user:
        execute("DELETE FROM refresh_tokens WHERE user_id=?", (user["id"],))
    resp = jsonify({"ok": True, "message": "Logged out"})
    unset_jwt_cookies(resp)
    return resp, 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    try:
        verify_jwt_in_request(refresh=True, locations=["headers", "cookies"])
    except Exception as e:
        return err(str(e), 401)
    uid  = get_jwt_identity()
    user = query("SELECT * FROM users WHERE id=? AND is_active=1", (uid,), fetchone=True)
    if not user:
        return err("This user account could not be found", 401)
    access_token = create_access_token(identity=str(user["id"]))
    resp = jsonify({"ok": True, "access_token": access_token})
    set_access_cookies(resp, access_token)
    return resp, 200


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    user = get_current_user()
    if not user:
        return err("The item could not be found", 401)
    return ok({"user": safe_user(user)})


@auth_bp.route("/me", methods=["PUT"])
@require_auth
def update_profile():
    user   = get_current_user()
    data   = request.get_json(silent=True) or {}
    fields = []
    values = []
    for col in ("full_name", "email", "department", "shift_start", "shift_end"):
        if col in data:
            fields.append("{}=?".format(col))
            values.append(str(data[col]).strip())
    if data.get("password"):
        if len(data["password"]) < 8:
            return err("Your password must be at least 8 characters long")
        fields.append("password_hash=?")
        values.append(bcrypt.generate_password_hash(data["password"]).decode())
    if not fields:
        return err("No changes were detected")
    fields.append("updated_at=datetime('now')")
    values.append(user["id"])
    execute("UPDATE users SET {} WHERE id=?".format(", ".join(fields)), values)
    updated = query("SELECT * FROM users WHERE id=?", (user["id"],), fetchone=True)
    return ok({"user": safe_user(updated)}, "Profile updated")