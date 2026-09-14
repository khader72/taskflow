import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE"] = path
    os.environ["SECRET_KEY"] = "test-secret"
    app = create_app()
    app.config.update(TESTING=True)
    yield app
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_token(client):
    client.post("/register", json={"username": "alice", "password": "secret123"})
    resp = client.post("/login", json={"username": "alice", "password": "secret123"})
    return resp.get_json()["token"]
