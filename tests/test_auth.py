def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_register_and_login(client):
    r = client.post("/register", json={"username": "bob", "password": "pw12345"})
    assert r.status_code == 201
    r = client.post("/login", json={"username": "bob", "password": "pw12345"})
    assert r.status_code == 200
    assert "token" in r.get_json()


def test_login_wrong_password(client):
    client.post("/register", json={"username": "carol", "password": "pw12345"})
    r = client.post("/login", json={"username": "carol", "password": "WRONG"})
    assert r.status_code == 401


# --- Module 08 (Semgrep finds F1b): written by the learner. FAILS against the vulnerable
# login (a single quote breaks the SQL -> HTTP 500), PASSES once the query is parameterized.
# Note: ' OR 1=1 -- does NOT bypass login thanks to bcrypt (defense in depth), so we test
# the injectability itself, not the bypass. ---
def test_login_rejects_quote_without_crashing(client):
    r = client.post("/login", json={"username": "'", "password": "whatever"})
    assert r.status_code == 401, f"SQL injection: expected 401, got {r.status_code}"
