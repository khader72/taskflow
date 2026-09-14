import datetime
from functools import wraps

import bcrypt
import jwt
from flask import Blueprint, current_app, g, jsonify, request

from .db import get_db

auth_bp = Blueprint("auth", __name__)


def make_token(user_id, is_admin):
    payload = {
        "sub": user_id,
        "admin": bool(is_admin),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def login_required(admin=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify({"error": "missing token"}), 401
            token = header.split(" ", 1)[1]
            try:
                payload = jwt.decode(
                    token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
                )
            except jwt.PyJWTError:
                return jsonify({"error": "invalid token"}), 401
            g.user_id = payload["sub"]
            g.is_admin = payload.get("admin", False)
            if admin and not g.is_admin:
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, pw_hash),
        )
        db.commit()
    except Exception:
        return jsonify({"error": "user already exists"}), 409
    return jsonify({"status": "created"}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    db = get_db()
    # F1b (intentional): SQL Injection in login. The username is concatenated straight into
    # the query. NOTE: the classic  ' OR 1=1 --  does NOT bypass login here, because bcrypt
    # verifies the password separately below (defense in depth!). But the query IS injectable:
    # a single quote crashes with HTTP 500, and a UNION with an attacker-controlled bcrypt
    # hash can still log in. Semgrep flags it in Module 08 ("the scanner found what our eyes
    # missed"). Fixed with a parameterized query + test_login_rejects_quote_without_crashing.
    query = "SELECT * FROM users WHERE username = '%s'" % username
    row = db.execute(query).fetchone()

    if row is None:
        return jsonify({"error": "invalid credentials"}), 401
    if not bcrypt.checkpw(password.encode(), row["password"].encode()):
        return jsonify({"error": "invalid credentials"}), 401

    token = make_token(row["id"], row["is_admin"])
    return jsonify({"token": token})


@auth_bp.get("/admin/users")
@login_required(admin=True)
def list_users():
    db = get_db()
    rows = db.execute("SELECT id, username, is_admin FROM users").fetchall()
    return jsonify([dict(r) for r in rows])
