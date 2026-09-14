def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_tasks(client, auth_token):
    r = client.post("/tasks", json={"title": "Learn DevSecOps"}, headers=_auth(auth_token))
    assert r.status_code == 201
    r = client.get("/tasks", headers=_auth(auth_token))
    titles = [t["title"] for t in r.get_json()]
    assert "Learn DevSecOps" in titles


def test_tasks_require_auth(client):
    assert client.get("/tasks").status_code == 401


# --- Module 04 (Break it #1): SQL Injection in task search (F1). Written by the learner
# with Claude Code. FAILS against the vulnerable code (user 2 sees user 1's task through
#   /tasks?q=%' OR 1=1 --  ), PASSES once the search uses a parameterized query. ---
def test_search_sql_injection_cannot_leak_other_users_tasks(client):
    client.post("/register", json={"username": "s1", "password": "pw12345"})
    client.post("/register", json={"username": "s2", "password": "pw12345"})
    t1 = client.post("/login", json={"username": "s1", "password": "pw12345"}).get_json()["token"]
    t2 = client.post("/login", json={"username": "s2", "password": "pw12345"}).get_json()["token"]
    client.post("/tasks", json={"title": "s1 secret plan"}, headers=_auth(t1))

    r = client.get("/tasks", query_string={"q": "%' OR 1=1 --"}, headers=_auth(t2))
    assert r.status_code == 200
    titles = [t["title"] for t in r.get_json()]
    assert "s1 secret plan" not in titles, "SQL injection leaked another user's tasks!"


# --- Module 15 (or Module 04 challenge): IDOR regression test. Written by the learner.
# Fails against the vulnerable code because /tasks/<id> ignores ownership. ---
def test_cannot_read_another_users_task(client):
    client.post("/register", json={"username": "u1", "password": "pw12345"})
    client.post("/register", json={"username": "u2", "password": "pw12345"})
    t1 = client.post("/login", json={"username": "u1", "password": "pw12345"}).get_json()["token"]
    t2 = client.post("/login", json={"username": "u2", "password": "pw12345"}).get_json()["token"]

    created = client.post("/tasks", json={"title": "u1 private"}, headers=_auth(t1)).get_json()
    task_id = created["id"]

    r = client.get(f"/tasks/{task_id}", headers=_auth(t2))
    assert r.status_code in (403, 404), "IDOR: user 2 could read user 1's task!"
