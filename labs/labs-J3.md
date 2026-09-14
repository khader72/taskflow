# STEP 7 — Labs — Day 3 (Modules 09–12)

Structure : **Title · Objective · Scenario · Prerequisites · Architecture · Tasks · Commands · Files · Expected result · Security lesson · Troubleshooting · Challenge**.

---

## LAB 09 — Know What You Ship (Lab IA)

**Objective** — Générer un SBOM, scanner l'image en CI, et trier un rapport de vulnérabilités avec Claude Code — en détectant une mauvaise priorisation.

**Scenario** — Une nouvelle CVE fait la une. Direction : « Sommes-nous touchés, et par quoi exactement ? »

**Prerequisites** — Lab 08 ; Trivy, Syft.

**Architecture** — Image durcie → Syft (SBOM) + Trivy (scan) en CI → triage assisté.

**Tasks**
1. Ajouter un job `sbom` (Syft → artifact) et un job `image-scan` (Trivy, échec sur CRITICAL).
2. **Ask** : donner le rapport Trivy à Claude Code, demander une priorisation argumentée (exploitable ? exposé ? correctif ?).
3. **Verify** : un CVE est volontairement mal priorisé par l'exercice — le repérer et le contester.
4. **Fix** : appliquer le plan (bump de versions), rebuild, rescanner, comparer.

**Commands**
```bash
syft taskflow:hardened -o spdx-json > sbom.json
trivy image --severity HIGH,CRITICAL taskflow:hardened | tee docs/security/trivy-triage.txt
# Ask Claude Code: "Prioritise these findings for a public-facing Flask API. Justify."
# ... appliquer, puis :
docker build -t taskflow:patched .
trivy image --severity HIGH,CRITICAL taskflow:patched
```

**Files** — jobs `ci.yml` :
```yaml
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: anchore/sbom-action@v0
        with: { format: spdx-json, output-file: sbom.json }
      - uses: actions/upload-artifact@v6
        with: { name: sbom, path: sbom.json }
  image-scan:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: aquasecurity/trivy-action@0.36.0
        with:
          image-ref: ghcr.io/${{ github.repository }}:sha-${{ github.sha }}
          severity: CRITICAL
          exit-code: "1"
```
`docs/ai-log.md` : entrée triage, dont le CVE mal priorisé repéré.

**Expected result** — SBOM attaché à chaque build ; `image-scan` bloque sur CRITICAL ; le plan de remédiation est appliqué et prouvé par un rescan.

**Security lesson** — 80–90 % d'une app est du code tiers. Un SBOM répond en secondes à « sommes-nous touchés ? ». La gravité dépend du contexte, pas seulement du score CVSS — et l'IA aide à trier à condition de la challenger.

**Troubleshooting**
- Trivy DB ne se télécharge pas (réseau) : pré-télécharger `trivy image --download-db-only`.
- Beaucoup de CVE sans correctif : les marquer « accepté, pas de fix upstream » dans le triage, avec justification.

**Challenge** — Signer l'image avec `cosign sign` (mode keyless local) et vérifier la signature.

---

## LAB 10 — No Secrets Left Behind (Break it to secure it #4)

**Objective** — Retirer tout secret du code, de l'historique Git et de l'image, et empêcher la récidive.

**Scenario** — Gitleaks a signalé un secret la semaine dernière. Il faut nettoyer *et* garantir que ça ne se reproduit pas.

**Prerequisites** — Lab 09.

**Architecture** — `.env` (ignoré) + GitHub Secrets + pre-commit Gitleaks.

**Tasks**
1. **Detect** : retrouver la `SECRET_KEY` (F3) dans l'historique et un éventuel secret dans l'image.
2. **Fix** : externaliser vers `.env`, compléter `.gitignore`, injecter via Compose `env_file`, créer les GitHub Secrets pour GHCR.
3. **Rotate** : régénérer `SECRET_KEY`, considérer l'ancienne comme compromise.
4. **Prevent** : installer Gitleaks en pre-commit.
5. Documenter la procédure.

**Commands**
```bash
git log -p | grep -i "secret" | head
docker history --no-trunc ghcr.io/<user>/taskflow:dev | grep -i secret || true
python -c "import secrets; print(secrets.token_hex(32))"   # nouvelle clé
cat > .env <<EOF
SECRET_KEY=<nouvelle-cle>
DATABASE=/app/data/taskflow.db
EOF
echo ".env" >> .gitignore
pip install pre-commit
cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
EOF
pre-commit install
git add .gitignore .pre-commit-config.yaml && git commit -m "chore: externalize secrets + gitleaks pre-commit"
```

**Files** — `.env` (non commité), `.gitignore` complété, `.pre-commit-config.yaml`, `docs/security/secrets.md`. Retirer le fallback dans `app/__init__.py` :
```python
# Avant : os.environ.get("SECRET_KEY", "dev-secret-please-change")
# Après :
key = os.environ.get("SECRET_KEY")
if not key:
    raise RuntimeError("SECRET_KEY is required")
app.config["SECRET_KEY"] = key
```

**Expected result** — Gitleaks vert sur l'historique post-rotation ; l'app refuse de démarrer sans `SECRET_KEY` ; un commit contenant un secret est bloqué par le hook.

**Security lesson** — Un secret commité est compromis pour toujours : il faut le **faire tourner**, pas seulement le supprimer. Le pre-commit hook est le contrôle le plus « à gauche » possible.

**Troubleshooting**
- Compose ne lit pas `.env` : ajouter `env_file: [.env]` au service.
- Nettoyer l'historique en profondeur (git-filter-repo) : hors périmètre débutant ; ici on **rotate**, ce qui rend l'ancien secret inutile.

**Challenge** — Remplacer les variables d'env par des *Docker secrets* (fichier monté en lecture seule) et adapter l'application.

---

## LAB 11 — Deliver, Then Attack It (Break it to secure it #5)

**Objective** — Promouvoir l'image vers `staging` avec approbation, puis tester l'application déployée avec OWASP ZAP et corriger les security headers.

**Scenario** — On passe de « ça build » à « c'est livré en staging et testé comme par un attaquant ».

**Prerequisites** — Lab 10.

**Architecture** — GHCR `sha` → (approbation) → tag `staging` → déploiement local ; job `dast` (ZAP baseline).

**Tasks**
1. Créer l'environnement GitHub `staging` avec *required reviewer*.
2. Ajouter `cd.yml` : retag `sha` → `staging` après approbation.
3. Déployer en local (`docker compose pull && up`).
4. Ajouter un job `dast` (ZAP baseline contre l'app démarrée en service).
5. **Break/Fix** : corriger les security headers manquants (via nginx ou Flask-Talisman) ; rescanner.

**Commands**
```bash
# Local DAST rehearsal
docker compose up -d
docker run --rm -t --network host ghcr.io/zaproxy/zaproxy zap-baseline.py \
  -t http://localhost:5000 | tee docs/security/zap-before.txt
```

**Files** — `cd.yml` :
```yaml
name: CD
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
jobs:
  promote-staging:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    environment: staging          # required reviewer configuré dans GitHub
    steps:
      - uses: docker/login-action@v4
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - run: |
          docker pull ghcr.io/${{ github.repository }}:sha-${{ github.sha }}
          docker tag ghcr.io/${{ github.repository }}:sha-${{ github.sha }} ghcr.io/${{ github.repository }}:staging
          docker push ghcr.io/${{ github.repository }}:staging
  dast:
    needs: [promote-staging]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: docker compose up -d && sleep 5
      - uses: zaproxy/action-baseline@v0.15.0
        with: { target: "http://localhost:5000", fail_action: true }
```
Correctif headers (Flask-Talisman) dans `app/__init__.py` :
```python
from flask_talisman import Talisman
Talisman(app, content_security_policy=None)  # ajoute X-Frame-Options, X-Content-Type-Options, HSTS...
```

**Expected result** — Promotion possible seulement après approbation ; ZAP baseline sans alerte *High* après ajout des headers.

**Security lesson** — CI ≠ CD ≠ Continuous Deployment. On construit une fois, on promeut le même artifact. Le DAST voit ce que le SAST ne voit pas : les headers et le comportement de l'app réelle.

**Troubleshooting**
- ZAP « connection refused » : augmenter le `sleep`, vérifier que l'app écoute sur `0.0.0.0` dans le container.
- `flask-talisman` casse en HTTP local : `Talisman(app, force_https=False)` en dev.

**Challenge** — Implémenter un rollback : redéployer le tag `sha` précédent en une commande, et le documenter dans un runbook.

---

## LAB 12 — Infrastructure You Can Review (Break it to secure it #6)

**Objective** — Décrire l'infra locale de TaskFlow en Terraform (`kreuzwerker/docker`), relire et garder cette infra comme du code (revue + garde-fous natifs), scanner ce que le scanner sait scanner (le Dockerfile, avec Checkov) et intégrer le scan en CI.

**Scenario** — L'infra « bricolée à la main » n'est ni relisible ni auditable. On la passe en code — et on découvre qu'un scanner ne voit pas tout.

**Prerequisites** — Lab 11 ; Terraform ≥ 1.5, Checkov.

**Architecture** — `infra/main.tf` : `docker_network`, `docker_volume`, `docker_image`, `docker_container` (app) + blocs `check` Terraform ; Checkov sur `Dockerfile`.

**⚠️ Note de conception (vérifiée en test)** — Checkov et `trivy config` n'ont **aucune règle** pour les ressources `docker_container` du provider kreuzwerker : sur le `main.tf` naïf ils renvoient 0 finding. C'est une vraie leçon professionnelle : *un scanner ne protège que ce qu'il sait lire*. Le lab est donc construit en trois couches : (a) **revue humaine** du HCL avec checklist, (b) **garde-fous natifs Terraform** (`check` blocks) qui rendent la misconfiguration visible au `plan`, (c) **Checkov sur le Dockerfile** (42 règles réelles) comme scan bloquant en CI.

**Tasks**
1. Écrire `infra/main.tf` en version **naïve** (`privileged = true`, port sur `0.0.0.0`, montage de `/var/run/docker.sock`).
2. `init` / `plan` / `apply`, vérifier que ça tourne.
3. **Detect (a)** : lancer `checkov -d infra/` → constater **0 finding**. Discussion : pourquoi ? (`checkov --list | grep docker_container` → rien). Puis **revue humaine** avec la checklist : privileged ? docker.sock ? `0.0.0.0` ? `user` ? tag `latest` ?
4. **Detect (b)** : ajouter les blocs `check` Terraform → `terraform plan` affiche maintenant des avertissements sur les trois misconfigurations.
5. **Fix** : corriger, `plan` (plus d'avertissement) → `apply`.
6. **Detect/Automate (c)** : `checkov -f Dockerfile` (findings réels, ex. `CKV_DOCKER_2` HEALTHCHECK) → corriger le Dockerfile → job `iac-scan` en CI (Checkov sur Dockerfile + `terraform validate`). Puis `destroy`.

**Commands**
```bash
cd infra
terraform init
terraform plan && terraform apply -auto-approve
checkov -d . ; checkov --list | grep -c docker_container      # 0 finding, 0 règle : angle mort
# ... ajouter les blocs check (voir Files), puis :
terraform plan                                                # => Warning: Check block assertion failed (x3)
# ... corriger main.tf ...
terraform plan && terraform apply -auto-approve               # plus d'avertissement
cd ..
checkov -f Dockerfile | tee docs/security/checkov-dockerfile-before.txt
# ... ajouter HEALTHCHECK au Dockerfile ...
checkov -f Dockerfile | tee docs/security/checkov-dockerfile-after.txt
cd infra && terraform destroy -auto-approve
```

**Files** — `infra/main.tf` (⚠️ provider **kreuzwerker/docker**, pas docker/docker) :
```hcl
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"   # Docker Engine LOCAL (pas Docker Hub)
      version = "~> 3.0"
    }
  }
}
provider "docker" {}

resource "docker_network" "taskflow" {
  name = "taskflow-net"
}
resource "docker_volume" "data" {
  name = "taskflow-data"
}
resource "docker_image" "app" {
  name = "ghcr.io/<user>/taskflow:staging"   # tag immuable, pas :latest
}
resource "docker_container" "app" {
  name  = "taskflow"
  image = docker_image.app.image_id
  user  = "10001"                    # non-root (correctif)
  networks_advanced { name = docker_network.taskflow.name }
  ports {
    internal = 5000
    external = 5000
    ip       = "127.0.0.1"           # pas 0.0.0.0 (correctif)
  }
  volumes {
    volume_name    = docker_volume.data.name
    container_path = "/app/data"
  }
  # privileged = true               # <-- à SUPPRIMER (misconfiguration)
  # volumes { host_path = "/var/run/docker.sock" ... }  # <-- NE JAMAIS monter
}

# ---- Garde-fous natifs (Policy as Code, Terraform >= 1.5) : visibles au `terraform plan`
check "no_privileged_container" {
  assert {
    condition     = !coalesce(docker_container.app.privileged, false)
    error_message = "docker_container.app must not run privileged."
  }
}
check "no_docker_socket_mount" {
  assert {
    condition     = length([for v in docker_container.app.volumes : v if try(v.host_path, "") == "/var/run/docker.sock"]) == 0
    error_message = "Never mount /var/run/docker.sock into an application container."
  }
}
check "ports_bound_to_localhost" {
  assert {
    condition     = alltrue([for p in docker_container.app.ports : p.ip != "0.0.0.0"])
    error_message = "Publish ports on 127.0.0.1, not 0.0.0.0."
  }
}
```
Correctif Dockerfile (finding Checkov `CKV_DOCKER_2`) :
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health').status==200 else 1)"
```
`iac-scan` dans `ci.yml` :
```yaml
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: bridgecrewio/checkov-action@v12
        with: { file: Dockerfile }               # ce que Checkov sait lire, en bloquant
      - uses: hashicorp/setup-terraform@v3
      - run: cd infra && terraform init -backend=false && terraform validate
```

**Expected result** — Version naïve : Checkov muet (0 règle pour ce provider) → la **revue humaine** trouve les 3 problèmes, puis les blocs `check` les affichent au `plan`. Version corrigée : `plan` sans avertissement. Dockerfile : Checkov passe de 1 échec (`HEALTHCHECK`) à 0 ; job `iac-scan` bloquant en CI.

**Security lesson** — Si l'infra est du code, on la relit, on la teste et on la scanne — avant qu'elle ne tourne (Shift Left appliqué à l'infra = Policy as Code). Deux leçons supplémentaires : **un scanner ne couvre que ce qu'il connaît** (toujours vérifier sa couverture : `checkov --list`), et quand l'outil manque, la revue humaine + des garde-fous écrits dans le code lui-même prennent le relais. Et attention : `kreuzwerker/docker` pilote le moteur local ; `docker/docker` gère Docker Hub.

**Troubleshooting**
- `terraform init` échoue : vérifier la source `kreuzwerker/docker`, pas `docker/docker`.
- Provider ne joint pas Docker : Docker Desktop doit tourner ; sous Linux, socket `/var/run/docker.sock` accessible à l'utilisateur.
- Le container déployé par Terraform ne répond pas sur `127.0.0.1:5000` : un volume nommé est créé *root*, l'app tourne en uid 10001 et ne peut pas écrire `taskflow.db`. Solutions : `DATABASE` sur un chemin inscriptible, ou initialiser le volume (`docker run --rm -v taskflow-data:/d alpine chown 10001 /d`), ou déclarer `user = "10001:10001"` **et** un `entrypoint` qui prépare le dossier.
- Les blocs `check` n'apparaissent pas : Terraform < 1.5 — mettre à jour.

**Challenge** — Faire échouer le `plan` (et non seulement avertir) : transformer un des `check` en `lifecycle { precondition { … } }` sur la ressource, alimenté par une `variable "privileged"` avec `validation`. Discuter : quand veut-on un avertissement, quand veut-on un blocage ?
