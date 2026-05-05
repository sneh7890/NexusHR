import functools
import datetime
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_current_user


def ok(data=None, message=None, status=200):
    body = {"ok": True}
    if message:
        body["message"] = message
    if data:
        body.update(data)
    return jsonify(body), status


def err(message, status=400):
    return jsonify({"ok": False, "message": message}), status


def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(locations=["headers", "cookies"])
        except Exception as e:
            return err(str(e), 401)
        return f(*args, **kwargs)
    return wrapper


def require_role(*roles):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request(locations=["headers", "cookies"])
            except Exception as e:
                return err(str(e), 401)
            user = get_current_user()
            if not user:
                return err("User not found", 401)
            if user["role"] not in roles:
                return err("Insufficient permissions", 403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.date.today().isoformat()


def secs_to_hms(secs):
    secs = max(0, int(secs))
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return "{:02d}:{:02d}:{:02d}".format(h, m, s)


def secs_to_decimal(secs):
    return round(secs / 3600, 2)