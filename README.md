# Module 12 — Calculations API
# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025

# Calculations API — Module Assignment

This repository implements a small FastAPI-based Calculations service for the Module 12 assignment. It demonstrates:

- REST API with FastAPI (OpenAPI/Swagger)
- SQLAlchemy ORM models (Postgres + SQLite for tests)
- Pydantic (v2) schemas and validation
- JWT authentication (access + refresh tokens)
- Redis-backed token blacklist for logout (aioredis stub used in tests)
- Basic UI template for quick manual testing
- Arithmetic operations including addition, subtraction, multiplication, division and power ($a^b$)


---

## 1. Module / Assignment Description

Implement an API that lets authenticated users create, read, update and delete arithmetic calculations. Each calculation stores:

- owner (`user_id`),
- type (`addition`, `subtraction`, `multiplication`, `division`, `power`),
- inputs (array of numbers), and
- computed `result`.

The API should validate inputs (e.g. division-by-zero prevention, `power` requires exactly two inputs). Authentication uses JWTs and logout must blacklist tokens in Redis. The UI exposes Swagger docs at `/docs` and ReDoc at `/redoc`.

Mathematically, the power operation is $a^b$ (base $a$ raised to exponent $b$). The server computes this exactly as $\text{result} = a^b$.

---

## 2. Quick Start — Run Locally (Recommended for development)

Prerequisites:

- Python 3.10+
- pip
- (optional) Docker & Docker Compose if you want Postgres + pgAdmin containers

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # Linux / macOS
# venv\Scripts\activate.bat  # Windows (PowerShell/CMD)
```

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Run the application (default local mode uses the repo settings):

```bash
# Start the FastAPI app (Swagger at http://127.0.0.1:8001/docs)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open the API docs in your browser:

- Swagger UI: `http://127.0.0.1:8001/docs`
- ReDoc: `http://127.0.0.1:8001/redoc`

If you prefer the app to use Postgres (and pgAdmin) locally, run the Docker services and point the app at Postgres (see section 4).

---

## 3. Run Tests and Coverage

Run unit/integration/e2e tests with pytest:

```bash
pytest -q
```

Generate coverage report (already integrated in pytest runs):

```bash
# show HTML coverage
pytest --cov=app
# coverage HTML will be written to htmlcov/
```

---

## 4. Run with Docker Compose (Postgres + pgAdmin)

This repo provides a `docker-compose.yml` that defines `db` (Postgres), `web` (the app) and `pgadmin`.

Start Postgres and pgAdmin (detached):

```bash
docker compose up -d db pgadmin
```

Create the tables in Postgres using the app's DB init helper:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/fastapi_db"
python -m app.database_init
```

Start the web service (inside Docker) or start your local app configured to point at Postgres.

Start the web container (Compose will read envs and the web container will create tables at startup):

```bash
docker compose up -d web
```

Open Swagger UI (web container maps port 8000):

```
http://localhost:8000/docs
```

Open pgAdmin (maps port 5050) and add a server with these connection details: the host is `db` when pgAdmin runs in the same Compose network, or `localhost` if connecting from your host.

- Host: `db` (or `localhost`)
- Port: `5432`
- Maintenance DB: `postgres` or `fastapi_db`
- Username: `postgres`
- Password: `postgres`

After you submit calculations from Swagger UI (docs), refresh the `calculations` table view in pgAdmin to see new rows.

---

## 5. Environment Variables

Key env vars used by the app (default values defined in `app/core/config.py`):

- `DATABASE_URL` — full SQLAlchemy DB URL. Examples:
  - `sqlite:///./test_db.sqlite` (default fallback for local dev/tests)
  - `postgresql://postgres:postgres@localhost:5432/fastapi_db`
- `REDIS_URL` — Redis URL used for token blacklist (e.g. `redis://localhost:6379`)
- `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `ALGORITHM` — JWT signing settings

Set the environment variable before starting the app if you want it to use Postgres:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/fastapi_db"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

---

## 6. Notes & Recommendations

- For production use, replace `Base.metadata.create_all()` with proper migrations (Alembic) as `create_all` is not suitable for destructive schema changes.
- The `aioredis` package is imported with a local stub to make tests run without a real Redis instance; CI uses a Redis service in GitHub Actions.
- If you see SQLAlchemy warnings about polymorphic identity during development when changing `calculation.type`, the update endpoint already performs a safe replace to avoid this issue.

---

