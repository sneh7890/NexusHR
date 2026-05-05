import sqlite3
import datetime
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.commit()
        db.close()


def row_to_dict(row):
    if row is None:
        return None
    result = {}
    for key in row.keys():
        val = row[key]
        if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
            result[key] = val.isoformat()
        else:
            result[key] = val
    return result


def query(sql, params=None, fetchone=False, fetchall=False):
    db = get_db()
    cur = db.execute(sql, params or ())
    if fetchone:
        row = cur.fetchone()
        return row_to_dict(row)
    if fetchall:
        rows = cur.fetchall()
        return [row_to_dict(r) for r in rows]
    return cur


def execute(sql, params=None):
    db = get_db()
    cur = db.execute(sql, params or ())
    return cur.rowcount


def execute_lastid(sql, params=None):
    db = get_db()
    cur = db.execute(sql, params or ())
    return cur.lastrowid


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'employee'
                  CHECK (role IN ('admin','manager','employee')),
    department    TEXT DEFAULT '',
    shift_start   TEXT DEFAULT '09:00',
    shift_end     TEXT DEFAULT '18:00',
    timezone      TEXT DEFAULT 'IST',
    is_active     INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT UNIQUE NOT NULL,
    expires_at  TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS timesheets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT NOT NULL,
    clock_in   TEXT,
    clock_out  TEXT,
    timezone   TEXT DEFAULT 'IST',
    status     TEXT NOT NULL DEFAULT 'active'
               CHECK (status IN ('active','completed')),
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS breaks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timesheet_id  INTEGER NOT NULL REFERENCES timesheets(id) ON DELETE CASCADE,
    break_in      TEXT NOT NULL,
    break_out     TEXT
);

CREATE TABLE IF NOT EXISTS spreadsheets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL DEFAULT 'Untitled Sheet',
    data        TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS otps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    otp_code    TEXT NOT NULL,
    purpose     TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used        INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shared_sheet (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL DEFAULT 'Shared Sheet',
    columns     TEXT NOT NULL DEFAULT '[]',
    data        TEXT NOT NULL DEFAULT '[]',
    updated_by  INTEGER REFERENCES users(id),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shared_sheet_rows (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sheet_id   INTEGER NOT NULL REFERENCES shared_sheet(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    row_index  INTEGER NOT NULL DEFAULT 0,
    data       TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS holidays (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_by  INTEGER REFERENCES users(id),
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shifts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    start_time  TEXT NOT NULL DEFAULT '09:00',
    end_time    TEXT NOT NULL DEFAULT '18:00',
    description TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'IST'",
    "ALTER TABLE timesheets ADD COLUMN timezone TEXT DEFAULT 'IST'",
    "ALTER TABLE users ADD COLUMN photo TEXT DEFAULT NULL",
]


def init_schema():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
    for m in MIGRATIONS:
        try:
            db.execute(m)
            db.commit()
        except Exception:
            pass
    print("Database ready.")