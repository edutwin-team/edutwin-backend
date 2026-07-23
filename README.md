<div align="center">

# EduTwin Backend

**API REST du jumeau numérique éducatif — simule le comportement d'apprentissage d'élèves virtuels via LLM pour aider les enseignants à tester leurs contenus pédagogiques avant diffusion.**

[![CI/CD Pipeline](https://github.com/edutwin-team/edutwin-backend/actions/workflows/ci-cd.yml/badge.svg?branch=main)](https://github.com/edutwin-team/edutwin-backend/actions/workflows/ci-cd.yml)
![Docker](https://img.shields.io/badge/docker-v1.2.0-blue?logo=docker)
[![Python](https://img.shields.io/badge/python-3.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2-092E20?logo=django)](https://www.djangoproject.com/)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen)](.coveragerc)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Démarrage rapide](#-démarrage-rapide) · [Architecture](#-architecture) · [API](#-documentation-api) · [CI/CD](#-cicd) · [Sécurité](#-sécurité) · [Contribuer](#-contribuer)

</div>

---

## 🎯 Qu'est-ce qu'EduTwin ?

Un enseignant crée un **jumeau numérique** (Digital Twin) : un élève virtuel défini par un profil comportemental (compréhension, motivation, fatigue, style d'apprentissage…) et un contexte pédagogique. Le backend fait ensuite **incarner ce profil par un LLM** (Groq / Llama 3.1) qui passe les quiz et lit les cours à la place de l'élève, puis restitue :

- un **score simulé** et le détail des réponses,
- un **feedback à la première personne** de l'élève virtuel,
- des **suggestions d'amélioration** des questions à destination de l'enseignant (clarté, distracteurs, difficulté).

Un **moteur de simulation déterministe** (pondération des traits comportementaux + bruit seedé) complète le LLM pour des résultats reproductibles.

## 🚀 Démarrage rapide

### Option A — Docker (recommandé)

```bash
git clone https://github.com/edutwin-team/edutwin-backend.git
cd edutwin-backend
cp .env.example .env   # renseigner SUPABASE_DB_URL, GROQ_API_KEY, SECRET_KEY
./start.sh             # docker compose up --build (API + worker Celery + Valkey)
```

### Option B — Environnement virtuel

```bash
git config core.hooksPath hooks       # active les hooks (anti-.env, ticket Jira)
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API disponible sur `http://127.0.0.1:8000` — healthcheck : `GET /health` → `{"status": "ok"}`.

## 🏗 Architecture

```
                        ┌─────────────────────────────────────────┐
  React/Vite (5173) ──▶ │            Django 5.2 + DRF             │
                        │  ┌────────┬────────┬─────────────────┐  │
                        │  │  user  │ twins  │    content      │  │
                        │  │  auth  │ profils│  cours & quiz   │  │
                        │  ├────────┴───┬────┴────┬────────────┤  │
                        │  │ simulation │ insights│  dashboard │  │
                        │  └─────┬──────┴─────────┴────────────┘  │
                        └────────┼───────────────┬────────────────┘
                                 ▼               ▼
                          Groq API          PostgreSQL
                       (Llama 3.1 8B)       (Supabase)
                                 │
                        Celery ──┴── Valkey/Redis (broker)
```

### Applications Django

| App | Rôle |
|---|---|
| `user` | Utilisateur custom (email + rôles admin/teacher/student), inscription avec **vérification e-mail par token**, session auth, profils éducatifs |
| `twins` | `DigitalTwin`, `Behavior` (14 traits comportementaux 0–100), `PedagogicalContext` + objectifs |
| `content` | Cours, quiz, questions/réponses typés, permissions par créateur |
| `simulation` | Moteur déterministe (`engine.py`) + client LLM (`groq_client.py`), résultats persistés |
| `insights` / `dashboard` | Agrégations et restitution pour le front |

### Stack technique

| Couche | Techno | Pourquoi |
|---|---|---|
| API | Django 5.2 + DRF 3.17 | Batteries incluses : ORM, admin, migrations, auth session |
| BDD | PostgreSQL (Supabase) via `dj-database-url` | Managée, SQLite `:memory:` auto en CI (`GITHUB_ACTIONS=true`) |
| Tâches async | Celery 5.5 + Valkey (broker) + `django-celery-results` | Simulations LLM longues hors requête HTTP |
| IA | Groq — `llama-3.1-8b-instant` | Latence très faible, sortie JSON structurée parsée/validée |
| Docs API | drf-spectacular (OpenAPI 3) | Schéma auto → Swagger + Redoc |
| Serveur | Gunicorn + WhiteNoise | Statiques servis sans CDN, adapté à Render |
| Qualité | mypy + django-stubs, coverage (**seuil 90 %**), hooks git | Typage vérifié en CI, pas de `.env` commité, ticket Jira obligatoire |

## 📖 Documentation API

| URL | Contenu |
|---|---|
| `/api/docs/` | Swagger UI interactif |
| `/api/redoc/` | Redoc |
| `/api/schema/` | Schéma OpenAPI brut ([`schema.yml`](schema.yml) versionné) |

Routes principales : `/api/auth/` · `/api/twins/` · `/api/content/` · `/api/simulation/` · `/api/insights/` · `/api/dashboard/`

Exemple — lancer une simulation de quiz :

```http
POST /api/simulation/quiz/
{ "twin_id": 3, "quiz_id": 7 }
→ 201 { "simulated_score": 62.5, "answer_details": [...], "llm_feedback": "..." }
```

## ⚙️ CI/CD

Pipeline GitHub Actions ([`ci-cd.yml`](.github/workflows/ci-cd.yml)) déclenché sur push/PR vers `main` et `develop` :

```
 push/PR ──▶ quality ──▶ test ──▶ build-and-push ──▶ deploy
             lint,       coverage   Docker Hub         Render
             migrations, ≥ 90 %     (buildx + cache    deploy hook
             mypy                    GHA, tag SHA)     (curl + retry)
```

1. **`quality`** — `manage.py check`, détection de migrations manquantes (`makemigrations --check`), type-check mypy. Fail-fast, timeout 10 min.
2. **`test`** — tests Django + coverage, **échec si < 90 %**, rapport XML archivé en artefact.
3. **`build-and-push`** *(push uniquement)* — build Buildx avec cache GitHub Actions, push vers [`mish1ma/edutwin-backend`](https://hub.docker.com/r/mish1ma/edutwin-backend). Tags : `latest` (main), `dev` (develop), **`sha-<commit>` immuable → rollback possible**.
4. **`deploy`** — déclenche le deploy hook **Render** de l'environnement correspondant via GitHub Environments (`production` / `development`, secrets scopés + approbation manuelle possible).

Optimisations : `concurrency` annule les runs redondants sur une même PR ; la CI bascule automatiquement sur SQLite en mémoire (zéro secret requis pour les tests).

### Image Docker

Image `python:3.14-slim`, exécution **non-root** (utilisateur `django`), `entrypoint.sh` en prod : `migrate` → `collectstatic` → Gunicorn 2 workers sur `$PORT`.

## 🔒 Sécurité

- **CSRF** : `CsrfViewMiddleware` + endpoint `GET /api/csrf/` pour le front SPA ; `CSRF_TRUSTED_ORIGINS` par env.
- **Sessions** : cookies `HttpOnly` (anti-XSS), `Secure` en prod, `SameSite=Lax`.
- **Rate limiting** : throttling DRF — `5000/jour` par utilisateur, `100/h` anonyme.
- **Auth/roles** : `IsAuthenticated` par défaut ; permissions custom `IsAdminOrTeacherOrReadOnly`, `IsOwnerOrAdmin`.
- **Vérification e-mail** : compte inactif tant que le lien d'activation (uid base64 + token Django) n'est pas cliqué.
- **Secrets** : `SECRET_KEY` obligatoire en prod (levée d'exception sinon), hook pre-commit bloquant tout `.env`, conteneur non-root.
- **CORS** : origines explicites par environnement, `django-cors-headers`.

## 🔧 Variables d'environnement

| Variable | Requis | Description |
|---|---|---|
| `SUPABASE_DB_URL` | ✅ (hors CI) | URL PostgreSQL |
| `GROQ_API_KEY` | ✅ | Clé API Groq (simulations LLM) |
| `SECRET_KEY` | ✅ en prod | Clé Django |
| `ENVIRONMENT` | — | `development` (défaut) / `production` |
| `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` | prod | Origines front, séparées par virgules |
| `CELERY_BROKER_URL` | — | Défaut `redis://localhost:6379/0` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | e-mails | SMTP pour l'activation de compte |

Voir [`.env.example`](.env.example).

## 🧪 Tests

```bash
coverage run manage.py test -v 2
coverage report   # échoue sous 90 % (voir .coveragerc)
mypy . --ignore-missing-imports
```

## 🤝 Contribuer

Workflow **feature branch → PR → `develop` → `main`**, squash & merge, review obligatoire, jamais de push direct sur `main`/`develop`.

```bash
git checkout develop && git pull
git checkout -b feature/ma-feature-EDT-42
git commit -m "feat: ajouter X EDT-42"   # le hook commit-msg exige EDT-XXX
```

Détails complets (conventions, mise à jour de branche, protection) : [CONTRIBUTING.md](CONTRIBUTING.md) · Template de PR : [`.github/pull_request_template.md`](.github/pull_request_template.md)

## 📄 Licence

[MIT](LICENSE) © 2026 edutwin-team
