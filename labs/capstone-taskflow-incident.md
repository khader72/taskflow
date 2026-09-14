# STEP 7 — Capstone Lab — TaskFlow-Incident (Day 5)

Voir aussi `05-Capstone.md` (grille de 14 findings, évaluation). Ce fichier est la fiche de lab remise aux équipes.

---

## LAB TITLE — TaskFlow-Incident: From Incident to Continuous Security

**Objective** — En équipe de 2–3, remettre en conformité une version dégradée de TaskFlow et **prouver** le résultat par un pipeline entièrement vert.

**Scenario** — « Vous rejoignez l'équipe TaskFlow. Vendredi dernier, le staging a été compromis (fuite de tâches, création d'un compte admin). Un collègue a désactivé le pipeline "pour aller plus vite" et poussé des correctifs à la main. Le prestataire IA a laissé un `CLAUDE.md` que personne n'a relu. Remettez le projet en état — et prouvez-le. »

**Prerequisites** — Modules 01–16 ; dépôt `taskflow-incident` (template) ; Claude Code.

**Architecture** — Identique à TaskFlow, mais avec 14 régressions volontaires (code, image, IaC, pipeline, secrets, ops, IA).

**Tasks**
1. **Identify (08h45–10h30)** : lancer *tous* les outils de la semaine + lecture humaine ; matrice impact/effort → `docs/capstone/findings.md`.
2. **Remediate (10h45–12h30)** : une PR par famille ; Claude Code en assistant ; test/scan pour chaque PR ; réactiver le pipeline avec tous les gates.
3. **Prove (13h55–15h30)** : pipeline vert sur `main` (lint, test, gitleaks, semgrep, pip-audit, trivy, sbom, zap, checkov) ; branch protection ; threat model à jour ; détection réactivée.
4. **Present (15h45–17h00)** : 10 min par équipe.

**Commands** (batterie d'audit initiale)
```bash
gitleaks detect --source . --redact
semgrep --config p/owasp-top-ten .
pip-audit -r requirements.txt
trivy image taskflow-incident:latest
checkov -d infra/
pytest -q
python attack-tools/bruteforce.py http://localhost:5000 alice
```

**Files** — `docs/capstone/findings.md`, PRs de remédiation, captures des scans verts, threat model mis à jour.

**Expected result** — Les 14 findings (ou ≥ 12 dont I13 la prompt injection et I14 la dépendance hallucinée) identifiés, corrigés, pipeline entièrement vert, branch protection active.

**Security lesson** — Tout le parcours en un jour : Shift Left, gates bloquants, secrets, supply chain, IaC, détection, réponse, et surtout **validation humaine de l'IA** (le `CLAUDE.md` piégé I13 et la dépendance hallucinée I14 sont les pièges décisifs).

**Troubleshooting** — Équipe bloquée sur l'environnement : utiliser la branche de solution du module correspondant dans `taskflow-solution`. Priorité aux findings à fort impact/faible effort d'abord.

**Challenge** — Atteindre le « niveau 2 » sur un axe OWASP SAMM : par exemple, signer l'image (Cosign) et vérifier la signature dans le pipeline de déploiement.

---

## Grille des 14 findings (rappel formateur — ne pas distribuer)

Voir `05-Capstone.md` §3.2. Les deux findings décisifs pour le critère IA de la restitution : **I13** (prompt injection dans `CLAUDE.md`) et **I14** (`flask-jwt-secure-validator`, package inexistant).
