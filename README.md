# TaskFlow

A minimal task-management API used as the red-thread project of the **DevSecOps & AI-Augmented Security** training.

> ⚠️ This application contains **intentional security flaws** used for teaching. Do **not** deploy it as-is. Each flaw is fixed during a specific module (see the trainer's `05-Capstone.md`).

## Stack
- Python 3.12 · Flask · SQLite · PyJWT · bcrypt

## Run locally (Module 03)
```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: python -m venv .venv ; .venv\Scripts\activate
pip install -r requirements-dev.txt                  # app + pytest + ruff
python3 run.py
# API on http://localhost:5000  ·  Web UI on http://localhost:5000/
```
> Linux/macOS: use `python3`. Windows: use `python`. (Ubuntu has no `python` alias unless you install `python-is-python3`.)

Ouvrez ensuite http://localhost:5000/ dans un navigateur pour l'interface web.

## Quick test
```bash
curl -s localhost:5000/health
curl -s -X POST localhost:5000/register -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret123"}'
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s localhost:5000/tasks -H "Authorization: Bearer $TOKEN"
curl -s -X POST localhost:5000/tasks -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":"Learn DevSecOps"}'
```

## Tests
```bash
pytest -q
```

## Routes
| Method | Route | Auth | Description |
|---|---|---|---|
| GET | `/` | no | Web UI (interface de gestion des tâches) |
| GET | `/health` | no | Liveness |
| POST | `/register` | no | Create a user |
| POST | `/login` | no | Get a JWT token |
| GET | `/tasks` | yes | List your tasks |
| POST | `/tasks` | yes | Create a task |
| GET/PUT/DELETE | `/tasks/<id>` | yes | Read / update / delete a task |
| GET | `/admin/users` | admin | List users |
