# STEP 7 — Labs — Day 2 (Modules 05–08)

Structure : **Title · Objective · Scenario · Prerequisites · Architecture · Tasks · Commands · Files · Expected result · Security lesson · Troubleshooting · Challenge**.

---

## LAB 05 — Containerize TaskFlow

**Objective** — Emballer TaskFlow dans une image Docker, l'exécuter, la publier sur GHCR.

**Scenario** — « Ça marche sur ma machine » ne suffit pas : l'équipe veut une image reproductible.

**Prerequisites** — Lab 04 ; Docker fonctionnel ; login GHCR (`docker login ghcr.io`).

**Architecture**
```
Dockerfile → docker build → image taskflow:dev → docker run → container (port 5000)
docker-compose.yml : app + volume SQLite
GHCR : ghcr.io/<user>/taskflow:dev
```

**Tasks**
1. Écrire un Dockerfile **naïf** (volontairement imparfait — on le durcira au lab 06).
2. Construire et lancer l'image, tester avec `curl`.
3. Ajouter un volume pour persister `taskflow.db`.
4. Écrire `docker-compose.yml`.
5. Tag et push vers GHCR.

**Commands**
```bash
docker build -t taskflow:dev .
docker run --rm -p 5000:5000 taskflow:dev &
curl -s localhost:5000/health
docker compose up -d
echo $GHCR_PAT | docker login ghcr.io -u <user> --password-stdin
docker tag taskflow:dev ghcr.io/<user>/taskflow:dev
docker push ghcr.io/<user>/taskflow:dev
```

**Files**
`Dockerfile` (naïf, à durcir au lab 06) :
```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "run.py"]
```
`docker-compose.yml` :
```yaml
services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - taskflow-data:/app/data
    environment:
      - DATABASE=/app/data/taskflow.db
volumes:
  taskflow-data:
```

**Expected result** — `curl localhost:5000/health` répond depuis le container ; l'image est sur GHCR ; les tâches survivent au redémarrage grâce au volume.

**Security lesson** — Une image est un artifact qui partira en production. Ce qu'on met dedans (y compris par `COPY . .`) y reste — on le verra au lab 06.

**Troubleshooting**
- `denied: permission` au push GHCR : le PAT doit avoir `write:packages` ; rendre le package visible.
- Le volume ne persiste pas : vérifier que `DATABASE` pointe bien dans `/app/data`.

**Challenge** — Ajouter un service `nginx` en reverse proxy sur un réseau interne, n'exposer que nginx (port 8080), TaskFlow non exposé directement.

---

## LAB 06 — Harden the Image (Break it to secure it #2)

**Objective** — Détecter les failles de l'image naïve avec Trivy et durcir le Dockerfile sans casser l'application.

**Scenario** — Le scan de sécurité de l'entreprise refuse les images root avec des CVE critiques. Il faut durcir avant de pouvoir livrer.

**Prerequisites** — Lab 05.

**Architecture** — Image `taskflow:dev` (naïve) → Trivy → Dockerfile durci → `taskflow:hardened`.

**Tasks**
1. **Break/Detect** : scanner l'image naïve, compter les CRITICAL, vérifier `whoami`=root et la présence de fichiers indésirables via `docker history`.
2. **Secure** : image de base `slim`, utilisateur non-root, `.dockerignore`, versions épinglées.
3. **Verify** : rescanner, comparer, vérifier que l'app tourne toujours, y compris en `--read-only --cap-drop ALL`.
4. PR « chore: harden Dockerfile ».

**Commands**
```bash
mkdir -p docs/security   # vos livrables : ce dossier n'est pas fourni, vous le créez
trivy image taskflow:dev | tee docs/security/trivy-before.txt
docker run --rm taskflow:dev sh -c 'whoami'          # root
docker history taskflow:dev                          # repérer COPY . .
# ... durcir le Dockerfile + créer .dockerignore ...
docker build -t taskflow:hardened .
trivy image taskflow:hardened | tee docs/security/trivy-after.txt
docker run --rm taskflow:hardened sh -c 'whoami'     # app
# Système de fichiers en lecture seule : SQLite a besoin d'UN dossier inscriptible → on le monte explicitement
mkdir -p data
docker run --rm --read-only --cap-drop ALL \
  -v "$(pwd)/data:/app/data" -e DATABASE=/app/data/taskflow.db \
  -p 5000:5000 taskflow:hardened &
curl -s localhost:5000/health        # {"status":"ok"}
```

**Files**
`Dockerfile` durci :
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER app
EXPOSE 5000
CMD ["python", "run.py"]
```
`.dockerignore` :
```
.git
.venv
__pycache__
*.db
.env
docs
tests
```

**Expected result** — CRITICAL divisés par ~20 (mesuré : 56 → 3, image 1,63 Go → 216 Mo) ; `whoami` = `app` ; l'app répond en `--read-only --cap-drop ALL` **à condition** de lui donner un seul dossier inscriptible pour la base (`/app/data`) — c'est exactement le principe : tout en lecture seule sauf ce qui doit écrire.

**Security lesson** — Les 4 principes : **minimal** (base slim), **non-root** (`USER app`), **pinned** (versions figées), **scanned** (Trivy). `.dockerignore` empêche de copier `.env`, `.git` et les tests dans l'image.

**Troubleshooting**
- `--read-only` casse SQLite : monter un volume inscriptible pour `/app/data` (`-v $(pwd)/data:/app/data`).
- Toujours des CRITICAL : ce sont souvent des CVE de la base ; noter celles sans correctif dispo (triage, module 09).

**Challenge** — Multi-stage build : compiler les dépendances dans une étape `builder`, ne copier que le nécessaire dans l'image finale ; viser < 120 Mo (`docker images taskflow`).

---

## LAB 07 — Your First Pipeline

**Objective** — Écrire un workflow GitHub Actions qui lint, teste et construit l'image à chaque push.

**Scenario** — L'équipe veut que chaque changement soit vérifié automatiquement, pas « quand quelqu'un y pense ».

**Prerequisites** — Lab 06 ; dépôt sur GitHub.

**Architecture** — `push` / `pull_request` → job `lint` → `test` → `build` (push GHCR taggé par SHA).

**Tasks**
1. Créer `.github/workflows/ci.yml` avec les 3 jobs.
2. Pousser, observer l'onglet Actions.
3. Casser un test volontairement → PR rouge → corriger.
4. Ajouter un badge au README.

**Commands**
```bash
mkdir -p .github/workflows
# ... créer ci.yml ...
git add .github/workflows/ci.yml && git commit -m "ci: add lint/test/build pipeline"
git push
```

**Files** — `.github/workflows/ci.yml` :
```yaml
name: CI
on: [push, pull_request]
permissions:
  contents: read
  packages: write
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check .
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt pytest
      - run: pytest -q
  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - run: docker build -t ghcr.io/${{ github.repository }}:sha-${{ github.sha }} .
      - run: docker push ghcr.io/${{ github.repository }}:sha-${{ github.sha }}
```

**Expected result** — 3 jobs verts ; une image taggée par SHA sur GHCR ; badge visible dans le README.

**Security lesson** — Le pipeline est le premier reviewer infatigable, et le socle sur lequel viendront se brancher les security gates (lab 08). `permissions:` limite déjà les droits du workflow (Least Privilege).

**Troubleshooting**
- `ruff` échoue sur du code existant : corriger ou ajouter un `ruff.toml` minimal — ne pas désactiver le job.
- `build` ne pousse pas : vérifier `permissions: packages: write`.

**Challenge** — Ajouter un cache pip et une matrice Python 3.11 / 3.12 sur le job `test`.

---

## LAB 08 — Make the Pipeline Say No (Break it to secure it #3 · Lab IA)

**Objective** — Ajouter secrets scanning, SCA et SAST au pipeline, les voir bloquer, et rendre les gates obligatoires.

**Scenario** — Un audit exige que le pipeline refuse tout secret, toute dépendance vulnérable et tout pattern de code dangereux.

**Prerequisites** — Lab 07.

**Architecture** — `ci.yml` + jobs `gitleaks`, `pip-audit`, `semgrep` ; branch protection.

**Tasks**
1. Ajouter les 3 jobs de sécurité.
2. **Break** : commiter un faux token (format valide, valeur inventée), laisser `requests==2.25.1`, ajouter un `eval()` sur une entrée utilisateur → pipeline rouge.
3. **Ask/Verify** : demander à Claude Code d'expliquer chaque alerte et de proposer un correctif ; lire, corriger, re-pousser jusqu'au vert. **Surprise attendue** : Semgrep signale aussi la SQLi du login (`auth.py`, F1b) que personne n'avait corrigée au Lab 04 — le scanner a vu ce que nos yeux ont raté.
4. **Automate** : activer branch protection avec les 3 checks requis ; tenter de merger un secret → refusé.

**Commands**
```bash
# Break (dans une branche jetable)
# ⚠ ne PAS utiliser AKIAIOSFODNN7EXAMPLE : c'est la clé d'exemple officielle d'AWS, Gitleaks l'ignore volontairement.
echo 'AWS_KEY = "AKIA5J7Q2XZ9WBN3KLPD"' >> app/config_demo.py            # format AWS valide, valeur inventée
cat >> app/config_demo.py <<'EOF'
from flask import request
def calc():
    return eval(request.args.get("expr"))                                   # eval sur entrée utilisateur
EOF
git add app/config_demo.py && git commit -m "demo: trigger security gates" && git push
# Observer les échecs, puis corriger avec Claude Code, puis :
git rm app/config_demo.py && git commit -m "fix: remove insecure demo code" && git push
```

**Files** — jobs à ajouter dans `ci.yml` :
```yaml
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v3
        env: { GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with: { python-version: "3.12" }
      - run: pip install pip-audit
      - run: pip-audit -r requirements.txt
  sast:
    runs-on: ubuntu-latest
    container: { image: semgrep/semgrep }   # returntocorp/semgrep-action est archivé
    steps:
      - uses: actions/checkout@v5
      - run: >
          semgrep scan --error
            --config p/owasp-top-ten
            --config r/python.lang.security.audit.eval-detected
            --config r/python.flask.security.audit.debug-enabled
```
`docs/ai-log.md` (entrée du jour) documentant les alertes et leurs correctifs.

**Expected result** — Les 3 jobs échouent sur le code cassé ; après correctifs, tout est vert ; branch protection empêche de merger sans les checks. En détail :
- `gitleaks` : détecte `AKIA5J7Q2XZ9WBN3KLPD` (règle AWS).
- `sca` (`pip-audit`) : ~36 vulnérabilités dans 5 paquets, dont `requests 2.25.1` (F4) — mise à jour vers ≥ 2.32, et bump de `flask`, `pyjwt`, `urllib3`, `idna`.
- `sast` (Semgrep) : (1) la **SQLi du login** `auth.py` (`tainted-sql-string`, F1b) → correctif requête paramétrée + `test_login_rejects_quote_without_crashing` ; (2) `eval` sur entrée utilisateur (`eval-detected`) ; (3) `run.py` : `debug=True` (F5, règle `debug-enabled`) et `host="0.0.0.0"` (`avoid_app_run_with_bad_host`) → piloter `debug` par variable d'env (défaut `False`) et documenter que le `0.0.0.0` est voulu en container (exclusion justifiée dans `.semgrepignore` ou commentaire `# nosemgrep: <rule>` **avec justification**).

**Security lesson** — Un scan ne devient un *security gate* que s'il **bloque** (branch protection). C'est le moment où « DevSecOps » cesse d'être un mot : la sécurité est une étape du pipeline exécutée à chaque commit.

**Troubleshooting**
- Trop de faux positifs Semgrep : trier, documenter les exclusions dans `.semgrepignore` avec justification — ne pas désactiver la règle entière.
- Gitleaks ne voit pas le secret : `fetch-depth: 0` est requis pour scanner l'historique.

**Challenge** — Activer Dependabot (`.github/dependabot.yml`) et traiter sa première PR de mise à jour.
