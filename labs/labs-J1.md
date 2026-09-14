# STEP 7 — Labs — Day 1 (Modules 01–04)

Structure imposée : **Title · Objective · Scenario · Prerequisites · Architecture · Tasks · Commands · Files · Expected result · Security lesson · Troubleshooting · Challenge**.
Le code source de TaskFlow est dans `labs/taskflow-src/`.

---

## LAB 01 — Environment Check & Delivery Walkthrough

**Objective** — Valider que le poste est prêt et se représenter une chaîne de livraison de bout en bout.

**Scenario** — Premier jour dans une équipe DevSecOps : avant d'écrire la moindre ligne, on vérifie ses outils et on comprend « où va le code ».

**Prerequisites** — Poste avec droits d'installation ; checklist J-7 reçue.

**Architecture** — Poste local : Git, Docker, Python, Claude Code, compte GitHub.

**Tasks**
1. Vérifier chaque outil (commandes ci-dessous). Cocher la checklist.
2. Se connecter à GitHub, vérifier la 2FA.
3. Lancer Claude Code une première fois, poser une question simple pour valider l'accès.
4. En binôme, sur papier, placer les étapes d'une livraison (code → prod) et marquer d'une croix rouge où la sécurité intervient « avant DevSecOps » (à la fin) vs « avec DevSecOps » (partout).

**Commands**
```bash
git --version            # >= 2.40
docker run --rm hello-world
docker compose version   # v2.x
python3 --version        # 3.12.x  (Windows : python --version)
trivy --version
gitleaks version
semgrep --version
terraform version        # >= 1.6
checkov --version
claude --version         # Claude Code
```

**Files** — `checklist-env.md` (cochée), photo du schéma papier.

**Expected result** — Toutes les commandes répondent sans erreur ; le schéma montre la sécurité « à la fin » puis « partout ».

**Security lesson** — La sécurité intégrée tôt (Shift Left) coûte moins cher que la sécurité ajoutée à la fin. Le pipeline est l'endroit où on l'intègre.

**Troubleshooting**
- `docker: permission denied` (Linux) : ajouter l'utilisateur au groupe `docker` puis rouvrir la session.
- `hello-world` ne tire pas l'image : vérifier le réseau / proxy d'entreprise.
- Claude Code non authentifié : relancer `claude` et suivre le flux de connexion fourni par l'organisation.

**Challenge** — Écrire en une phrase, pour chaque étape du schéma, quel contrôle de sécurité on pourrait y placer. On y reviendra vendredi.

---

## LAB 02 — Classify the Risk

**Objective** — Utiliser correctement Asset / Threat / Vulnerability / Control et les relier à la CIA Triad.

**Scenario** — L'équipe fait une revue de risques éclair avant un déploiement.

**Prerequisites** — Module 02 (concepts).

**Architecture** — Aucune ; exercice sur cartes (fournies) ou tableur.

**Tasks**
1. Pour chacune des 12 situations fournies, poser l'étiquette : Asset, Threat, Vulnerability ou Control.
2. Relier chaque situation à C, I et/ou A.
3. En binôme, classer les 3 risques les plus élevés (probabilité × impact) et justifier.

**Commands** — Aucune.

**Files** — `docs/security/risk-classification.md` : **c'est vous qui créez ce fichier** (le dossier `docs/` n'est pas fourni dans le dépôt). Créez d'abord le dossier, rédigez la grille, puis committez-la au module 03 :
```bash
mkdir -p docs/security
$EDITOR docs/security/risk-classification.md   # rédiger la grille Asset/Threat/Vulnerability/Control
```

**Expected result** — Grille complétée ; accord du binôme sur le top 3 des risques.

**Exemples de cartes**
| Situation | Réponse attendue |
|---|---|
| La base de données des utilisateurs | Asset (C, I) |
| Un attaquant sur Internet | Threat |
| La SQL Injection du login | Vulnerability (C, I) |
| `bcrypt` sur les mots de passe | Control (C) |
| Le port 5000 exposé sur `0.0.0.0` | Vulnerability (C, I, A) |
| Un scan Trivy bloquant en CI | Control (C, I) |

**Security lesson** — Sans vocabulaire précis, une discussion de sécurité tourne en rond. « Menace » et « vulnérabilité » ne sont pas synonymes.

**Troubleshooting** — Hésitation Threat/Vulnerability : la menace *agit*, la vulnérabilité *permet*. « Attaquant » = threat ; « faiblesse exploitable » = vulnerability.

**Challenge** — Ajouter 3 cartes tirées de votre propre expérience professionnelle et les faire classer par le binôme.

---

## LAB 03 — Explore & Contribute (lancement du fil rouge)

**Objective** — Explorer TaskFlow en cours d'exécution depuis le terminal, puis contribuer via une Pull Request.

**Scenario** — On vous confie le dépôt TaskFlow. Avant de le modifier, vous devez le lancer, le comprendre, puis proposer votre première contribution proprement.

**Prerequisites** — Lab 01 validé ; compte GitHub.

**Architecture**
```
Navigateur / curl  →  Flask (port 5000)  →  SQLite (taskflow.db)
Poste local  →  git  →  GitHub (dépôt personnel)
```

**Tasks**
1. Créer votre dépôt depuis le template `taskflow` (*Use this template*), puis `git clone`.
2. Lancer l'application, la tester avec `curl`.
3. *Explore* : trouver le processus, le port en écoute, les permissions du fichier `taskflow.db`, lire une variable d'environnement, inspecter un certificat TLS d'un site public.
4. *Contribute* : créer une branche, améliorer le README (section « How to run »), commit, push, ouvrir une PR, la faire relire par le binôme, merger.

**Commands**
```bash
# Lancer  (Linux/macOS : python3 ; Windows : python)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt      # app + pytest + ruff
pytest -q                                # état initial attendu : 2 échecs volontaires (SQLi recherche, IDOR) + 1 (login quote)
python3 run.py &

# Explore
curl -s localhost:5000/health
ps aux | grep run.py
ss -tlnp | grep 5000
ls -l taskflow.db
env | grep -i secret        # observer : rien d'externalisé pour l'instant
openssl s_client -connect github.com:443 -servername github.com </dev/null 2>/dev/null | openssl x509 -noout -issuer -dates

# Contribute
git checkout -b feature/readme-$(whoami)
# ... éditer README.md ...
git add README.md && git commit -m "docs: clarify how to run TaskFlow locally"
git push -u origin feature/readme-$(whoami)
# Ouvrir la PR sur GitHub, review binôme, merge
```

**Files** — README.md modifié ; PR mergée.

**Expected result** — `GET /health` renvoie `{"status":"ok"}` ; vous savez citer le PID, le port, les permissions du `.db` ; une PR est mergée sur `main`.

**Security lesson** — La code review est le premier *security control* humain. Et savoir lire un système en cours d'exécution (ports, permissions, processus) est le préalable à toute analyse de sécurité.

**Troubleshooting**
- Port 5000 déjà utilisé (macOS AirPlay) : lancer `python run.py` après `export FLASK_RUN_PORT=5001`, ou libérer le port.
- `ss` absent (macOS) : utiliser `lsof -i :5000`.
- PR impossible à merger : vérifier que la branche est bien poussée et que vous êtes sur votre fork.

**Challenge** — Ajouter au README un diagramme ASCII du flux user → Flask → SQLite et le faire valider en review.

---

## LAB 04 — Break, Ask, Verify, Fix (Break it to secure it #1)

**Objective** — Exploiter la SQL Injection de la **recherche de tâches**, la corriger avec Claude Code, et **prouver** la correction par un test.

**Scenario** — Un utilisateur signale qu'en tapant un texte bizarre dans la recherche, il a vu les tâches d'autres personnes. Vous devez reproduire, comprendre, corriger et prouver.

**Prerequisites** — Lab 03 ; Claude Code authentifié.

**Architecture** — TaskFlow local ; `app/tasks.py` (recherche `GET /tasks?q=` vulnérable) ; `tests/test_tasks.py`.

**Tasks**
1. **Break** : créer deux utilisateurs, une tâche « secrète » pour le premier, puis, connecté en second, injecter dans `q` et voir la tâche du premier apparaître.
2. **Ask** : demander à Claude Code d'expliquer la vulnérabilité **et** d'écrire un test qui la démontre (`test_search_sql_injection_cannot_leak_other_users_tasks`, déjà présent — le faire échouer d'abord).
3. **Verify (fail)** : lancer `pytest`, constater que le test échoue contre le code vulnérable.
4. **Fix** : demander à Claude Code un correctif par requête paramétrée ; lire le diff.
5. **Verify (pass)** : relancer `pytest` ; le test doit passer, les autres aussi.
6. **Decide + Record** : ouvrir une PR « fix: SQL injection in task search », review binôme, merge ; noter l'échange dans `docs/ai-log.md`.

**Commands**
```bash
# Break — deux utilisateurs, une tâche secrète chez alice
API=localhost:5000
curl -s -X POST $API/register -H 'Content-Type: application/json' -d '{"username":"alice","password":"secret123"}'
curl -s -X POST $API/register -H 'Content-Type: application/json' -d '{"username":"mallory","password":"secret123"}'
TA=$(curl -s -X POST $API/login -H 'Content-Type: application/json' -d '{"username":"alice","password":"secret123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
TM=$(curl -s -X POST $API/login -H 'Content-Type: application/json' -d '{"username":"mallory","password":"secret123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -X POST $API/tasks -H "Authorization: Bearer $TA" -H 'Content-Type: application/json' -d '{"title":"alice secret plan"}'

# Mallory, recherche normale : ne voit rien
curl -s -G "$API/tasks" --data-urlencode "q=plan" -H "Authorization: Bearer $TM"        # => []
# Mallory, recherche INJECTÉE : voit la tâche d'alice
curl -s -G "$API/tasks" --data-urlencode "q=%' OR 1=1 --" -H "Authorization: Bearer $TM" # => [{"title":"alice secret plan",...}]

# Verify (doit échouer avant correction)
pytest tests/test_tasks.py::test_search_sql_injection_cannot_leak_other_users_tasks -q

# Après correction
pytest -q
git checkout -b fix/sqli-task-search
git add app/tasks.py && git commit -m "fix: use parameterized query in task search (SQLi)"
git push -u origin fix/sqli-task-search
```

**Files** — Correctif dans `app/tasks.py` ; `docs/ai-log.md` :
```markdown
## Lab 04 — SQLi recherche de tâches
- ASK: expliquer la SQLi + écrire un test d'exploitation
- READ: diff = passage de % (concaténation) à requête paramétrée (?)
- VERIFY: pytest -> le test d'exploitation PASSE (plus de fuite), 0 régression
- DECIDE: accepté
- NOTE IA: correct et minimal
```

**Expected result** — L'injection ne renvoie plus que les tâches de Mallory ; `pytest` : seul `test_cannot_read_another_users_task` (IDOR, challenge) et `test_login_rejects_quote_without_crashing` (Lab 08) restent rouges ; PR mergée.

**Correctif attendu** (référence formateur) — dans `app/tasks.py`, remplacer :
```python
sql = ("SELECT id, title, done FROM tasks "
       "WHERE owner_id = %d AND title LIKE '%%%s%%'" % (g.user_id, q))
rows = db.execute(sql).fetchall()
```
par :
```python
rows = db.execute(
    "SELECT id, title, done FROM tasks WHERE owner_id = ? AND title LIKE ?",
    (g.user_id, f"%{q}%"),
).fetchall()
```

**Security lesson** — Ne jamais construire une requête en collant des chaînes : la valeur ne doit jamais pouvoir changer la *structure* de la requête. Et surtout : un correctif n'est validé que par un test qui prouve la faille fermée. L'IA propose, le test prouve, l'humain décide.

**Pour le formateur — la deuxième injection (F1b)** : le login de `auth.py` concatène aussi le `username`. Le classique `' OR 1=1 --` n'y contourne **pas** l'authentification, parce que bcrypt vérifie le mot de passe séparément — c'est de la *defense in depth* en action. Mais une simple apostrophe fait planter le serveur (HTTP 500) et une injection `UNION` plus avancée reste possible. On la laisse volontairement : au Lab 08, Semgrep la trouvera (« le scanner a vu ce que nos yeux ont raté ») et `test_login_rejects_quote_without_crashing` servira de preuve. Si un apprenant rapide la repère dès aujourd'hui : bravo, c'est le challenge n°2.

**Troubleshooting**
- La recherche injectée renvoie `[]` : vérifier que la tâche d'alice a bien été créée (`curl $API/tasks -H "Authorization: Bearer $TA"`) et que le paramètre passe bien par `--data-urlencode` (le `%` et l'apostrophe doivent être encodés).
- Claude Code propose d'« échapper » les quotes ou de filtrer les caractères : refuser et exiger une requête paramétrée (expliquer pourquoi le filtrage est fragile).
- Claude Code corrige aussi le login au passage : accepter volontiers (c'est la même faille) — mais faire écrire le test correspondant.

**Challenge 1** — Même démarche (Break → Ask → Verify → Fix) sur l'IDOR de `GET /tasks/<id>` : faire échouer `test_cannot_read_another_users_task`, corriger en ajoutant `AND owner_id = ?`, prouver. *(Sinon, cette faille sera exploitée en module 15.)*

**Challenge 2** — Trouver la seconde injection dans `auth.py` (indice : essayez un `username` réduit à une apostrophe), expliquer pourquoi `' OR 1=1 --` n'y ouvre pourtant pas la porte, et la corriger avec `test_login_rejects_quote_without_crashing` comme preuve.
