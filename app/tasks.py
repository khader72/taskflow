from flask import Blueprint, g, jsonify, request

from .auth import login_required
from .db import get_db

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.get("/tasks")
@login_required()
def list_tasks():
    db = get_db()
    q = request.args.get("q")
    if q:
        # F1 (intentional): SQL Injection in task search. The search term is concatenated
        # into the query, so  q = %' OR 1=1 --  removes the owner filter and leaks EVERY
        # user's tasks (Information Disclosure). Fixed in Module 04 with a parameterized
        # query + a regression test (test_search_sql_injection_cannot_leak_other_users_tasks).
        sql = (
            "SELECT id, title, done FROM tasks "
            "WHERE owner_id = %d AND title LIKE '%%%s%%'" % (g.user_id, q)
        )
        rows = db.execute(sql).fetchall()
    else:
        rows = db.execute(
            "SELECT id, title, done FROM tasks WHERE owner_id = ?", (g.user_id,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@tasks_bp.post("/tasks")
@login_required()
def create_task():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (owner_id, title, done) VALUES (?, ?, 0)",
        (g.user_id, title),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "title": title, "done": 0}), 201


@tasks_bp.get("/tasks/<int:task_id>")
@login_required()
def get_task(task_id):
    db = get_db()
    # F2 (intentional): IDOR / Broken Access Control. The query fetches the task by id
    # but never checks that it belongs to g.user_id, so any authenticated user can read
    # anyone's task by changing the id. Fixed in Module 15 (and offered as the Module 04
    # challenge) by adding  AND owner_id = ?  .
    row = db.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@tasks_bp.put("/tasks/<int:task_id>")
@login_required()
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute(
        "SELECT id FROM tasks WHERE id = ? AND owner_id = ?", (task_id, g.user_id)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    db.execute(
        "UPDATE tasks SET title = COALESCE(?, title), done = COALESCE(?, done) WHERE id = ?",
        (data.get("title"), data.get("done"), task_id),
    )
    db.commit()
    return jsonify({"status": "updated"})


@tasks_bp.delete("/tasks/<int:task_id>")
@login_required()
def delete_task(task_id):
    db = get_db()
    row = db.execute(
        "SELECT id FROM tasks WHERE id = ? AND owner_id = ?", (task_id, g.user_id)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"status": "deleted"})
