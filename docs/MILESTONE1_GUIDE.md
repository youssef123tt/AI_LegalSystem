# Milestone 1 Guide (Beginner-Friendly)

This project is the start of an “Enterprise Legal Document RAG System”.
Milestone 1 sets up a **local development environment** and a **minimal API** so we have a solid foundation before adding ingestion, OCR, search, and chat.

If you are new to Docker, don’t worry: this guide explains what each file does, why it exists, and how everything fits together.

## What You Have Right Now

At the end of Milestone 1, you have:

- A **FastAPI** web server (“API service”) with:
  - `GET /healthz` (basic health check)
  - `GET /version` (shows app name + environment)
  - `GET /healthz/deps` (checks OpenSearch connectivity)
- A **worker service** (Celery) that will later run heavy background jobs like OCR and embedding.
- A **Docker Compose** setup to run these dependencies locally:
  - Postgres (database)
  - Redis (queue/broker)
  - OpenSearch (hybrid search engine: keyword + vector)
  - OpenSearch Dashboards (optional UI)

## Very Short Docker Primer

### Docker (simple definition)
Docker lets you run software in isolated “containers”.
A container is like a lightweight mini-computer with:

- its own filesystem
- its own installed packages
- a defined startup command

The big benefit is: your project works the same on different computers, because you run the same images/containers.

### Image vs Container

- **Image**: a template (like a “snapshot”) describing what to run.
- **Container**: a running instance created from an image.

### Docker Compose
Docker Compose is a tool to run **multiple containers together** (because a real app needs a database, a cache, search engine, etc).

In this repo, `infra/docker-compose.yml` describes all services and how they connect.

## Project Layout (Milestone 1)

These are the main files and folders currently present:

- `.gitignore`
- `.env.example`
- `.env`
- `README.md`
- `infra/docker-compose.yml`
- `scripts/dev.ps1`
- `apps/api/` (FastAPI service)
- `apps/worker/` (background job worker)
- `docs/MILESTONE1_GUIDE.md` (this file)

## File-by-File Explanation

### `.gitignore`
Purpose: tells Git which files should NOT be committed.

Important parts here:

- `.env` is ignored, because it often contains secrets (passwords, API keys).
- `data/` and logs are ignored.
- Python caches (`__pycache__`, `.pytest_cache`, etc.) are ignored.

### `.env.example`
Purpose: a “template” environment config file.

It contains example settings like:

- database user/password
- OpenSearch URL
- API port

You normally copy it to `.env` and then customize.

### `.env`
Purpose: your **local developer configuration**.

In Milestone 1, it includes defaults like:

- Postgres DB: `legal_rag`
- Postgres user/password: `legal` / `legal`
- OpenSearch URL: `http://opensearch:9200`

Because `.env` is in `.gitignore`, it stays local to your machine.

### `README.md`
Purpose: quick “how to run” instructions for the repo.

Right now it focuses on Milestone 1 and points you to run:

- `.\scripts\dev.ps1`

### `infra/docker-compose.yml`
Purpose: defines all containers/services we want to run locally, and how they connect.

This is the “brain” of the dev environment.

#### Services inside it

1. `postgres`
   - Runs a Postgres database.
   - Exposes port `5432` on your machine (so your API can connect).
   - Stores data in a named Docker volume `postgres_data` so it persists after restarts.

2. `redis`
   - Runs Redis, used as:
     - the queue broker for Celery (worker system)
     - the result backend for Celery (basic status storage)
   - Exposes port `6379`.

3. `opensearch`
   - Runs OpenSearch (search engine).
   - Exposes port `9200` (HTTP API) and `9600` (metrics).
   - Uses a named Docker volume `opensearch_data` to persist its index data.
   - `DISABLE_SECURITY_PLUGIN: "true"` is set to simplify local development.

4. `dashboards`
   - A UI for OpenSearch (optional).
   - Exposes port `5601`.
   - Depends on OpenSearch being healthy.

5. `api`
   - Builds the API container from `apps/api/Dockerfile`.
   - Depends on `postgres`, `redis`, `opensearch`.
   - Exposes port `8000` so you can open the API in your browser.
   - Sets environment variables for the app:
     - `DATABASE_URL`
     - `REDIS_URL`
     - `OPENSEARCH_URL`

6. `worker`
   - Builds the worker container from `apps/worker/Dockerfile`.
   - Depends on `postgres`, `redis`, `opensearch`.
   - Runs Celery. In Milestone 1 it does not process tasks yet (that comes later).

#### Ports (what you access on your machine)

- API: `http://localhost:8000`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`
- OpenSearch: `http://localhost:9200`
- Dashboards UI: `http://localhost:5601`

#### Healthchecks (what they are)
Each service has a “health check” so Docker knows when it is ready:

- Postgres: `pg_isready`
- Redis: `redis-cli ping`
- OpenSearch: tries to fetch `http://localhost:9200`

This helps avoid “API started too early” problems.

### `scripts/dev.ps1`
Purpose: easiest single command to run the dev environment.

What it does:

- If `.env` is missing, it prints a message and stops.
- If `.env` exists, it runs:
  - `docker compose -f .\infra\docker-compose.yml up --build`

Meaning:

- `up` starts services
- `--build` rebuilds the `api` and `worker` images from their Dockerfiles (so code changes get included)

### `apps/api/Dockerfile`
Purpose: describes how to build the API container image.

Key steps:

- Start from `python:3.12-slim`
- Copy `requirements.txt` and install dependencies
- Copy the application code (`app/`)
- Start the server using `uvicorn`

### `apps/api/requirements.txt`
Purpose: Python dependencies for the API.

Main packages:

- `fastapi`: web framework
- `uvicorn`: ASGI server (runs FastAPI)
- `pydantic-settings`: reads configuration from environment variables
- `opensearch-py`: OpenSearch client library
- `sqlalchemy` + `psycopg`: database access foundation (we will use more in Milestone 2+)

### `apps/api/app/settings.py`
Purpose: central configuration object for the API.

How it works:

- Reads environment variables (and `.env` file) into a `Settings` class.
- Exposes `settings` that code can import.

Examples of config values:

- `settings.database_url`
- `settings.opensearch_url`

### `apps/api/app/main.py`
Purpose: the FastAPI application entry point.

What it contains now:

- `app = FastAPI(...)`
- `GET /healthz`: returns `{"status":"ok"}`
- `GET /version`: returns app name and environment
- `GET /healthz/deps`: connects to OpenSearch and returns basic cluster info

This gives us:

- a quick way to verify API is alive (`/healthz`)
- a quick way to verify the search dependency is alive (`/healthz/deps`)

### `apps/worker/Dockerfile`
Purpose: describes how to build the worker container.

It installs worker requirements and runs Celery:

- `celery -A worker.celery_app:celery_app worker --loglevel=INFO`

### `apps/worker/requirements.txt`
Purpose: Python dependencies for the worker.

- `celery`: job processing framework
- `redis`: Redis client used by Celery

### `apps/worker/worker/celery_app.py`
Purpose: defines the Celery application (broker/backend).

It reads `REDIS_URL` and configures Celery to use Redis for:

- broker (task queue)
- backend (stores task results / status)

In Milestone 1 there are no tasks yet. In Milestone 2+ we’ll add ingestion tasks.

## How To Run Milestone 1 (Once Docker Is Installed)

You currently saw: `docker` is not recognized. That means Docker Desktop is not installed or not on PATH.

After installing Docker Desktop:

1. Open a **new PowerShell** (important: new session)
2. Verify Docker works:

```powershell
docker --version
docker compose version
```

3. Start the stack:

```powershell
.\scripts\dev.ps1
```

4. Test API endpoints in your browser:

- `http://localhost:8000/healthz`
- `http://localhost:8000/version`
- `http://localhost:8000/healthz/deps`

## Common Beginner Issues (and Fixes)

- Docker Desktop installed but `docker` still not found:
  - Close and reopen PowerShell
  - Restart your machine if needed
  - Ensure Docker Desktop is actually running

- Ports already in use:
  - Something else may already be using `8000`, `5432`, `9200`, etc.
  - We can change ports in `infra/docker-compose.yml` if necessary.

- OpenSearch needs more memory:
  - OpenSearch uses Java; it can be heavy.
  - If it crashes, we can reduce memory or adjust Docker Desktop resources.

## What’s Next (Milestone 2 Preview)

Milestone 2 will add:

- database tables (documents, jobs)
- file upload endpoint
- a worker task that processes an uploaded document

