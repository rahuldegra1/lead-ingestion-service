# Production Lead Ingestion & Observability Microservice

A hardened, containerized FastAPI microservice engineered with PostgreSQL persistence, zero-downtime Alembic migrations, constant-time API authentication, and a fully automated GitHub Actions CI/CD quality gate.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |           Internet Traffic            |
                      +---------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
              Public Health/Metrics              Protected Business Routes
           (GET /health, GET /metrics)             (POST /leads, GET /leads)
                        |                                   |
                        v                                   v
             [No Authentication Req.]           [X-API-Key Constant-Time Auth]
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                           +-----------------------------+
                           |  Observability Middleware   |
                           |  - Injects X-Request-ID     |
                           |  - Measures X-Process-Time  |
                           |  - Prometheus Latency Stats |
                           +-----------------------------+
                                          |
                                          v
                           +-----------------------------+
                           |     SlowAPI Rate Limiter    |
                           |       (Burst Control)       |
                           +-----------------------------+
                                          |
                                          v
                           +-----------------------------+
                           |   FastAPI Application Core  |
                           |    (Pydantic v2 Pipeline)   |
                           +-----------------------------+
                                          |
                                          v
                           +-----------------------------+
                           |   PostgreSQL 16 (Alembic)   |
                           |   - Composite B-Tree Index  |
                           |   - Isolated Connection Pool|
                           +-----------------------------+
```

---

## Core System Features

* **High-Throughput REST Ingestion**: Built on FastAPI and Pydantic v2 with custom data sanitizers that normalize phone numbers, enforce uppercase/lowercase formatting, and sanitize financial currency inputs.
* **Database & Migration Strategy**: Backed by PostgreSQL 16-alpine using SQLAlchemy ORM. Database schemas are tracked and provisioned automatically at startup via `alembic upgrade head`. Queries are optimized using composite B-tree indexes verified via `EXPLAIN ANALYZE`.
* **Constant-Time Authentication**: Secured with custom API key verification using Python's `secrets.compare_digest` to eliminate side-channel timing attacks across all protected lead ingestion and admin endpoints.
* **Probes & Observability**:
  * Public `/health` probe executing a live database ping (`SELECT 1`).
  * Public `/metrics` endpoint exposing Prometheus request rates, status codes, and latency histograms.
  * Custom HTTP middleware injecting distributed tracing headers (`X-Request-ID` and `X-Process-Time`) onto every response.
* **Traffic Throttling**: Route-level rate limiting using SlowAPI to mitigate denial-of-service attempts and uncontrolled ingestion bursts.

---

## Security & Container Hardening

The production container is built using a multi-stage `python:3.12-slim` image designed for a minimal attack surface:
* **Unprivileged Execution**: Runs under a dedicated, non-root user (`appuser`, UID `10000`) to prevent privilege escalation vulnerabilities.
* **Minimal Attack Surface**: Build dependencies and compilation toolchains are discarded in the builder stage, leaving only runtime wheels and stripped binaries in the final production artifact.
* **Container Healthchecks**: Leverages native Docker healthchecks probing `http://localhost:8000/health` with retry intervals and boot grace periods.

---

## Automated CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) enforces strict quality gates on every push to `main`:

1. **Lint & Test Job**:
   * **Ruff**: Enforces strict code formatting, unused import pruning, and PEP 8 compliance.
   * **Pytest Test Suite (14 Tests)**: Executes isolated unit and integration tests covering CRUD operations, sanitization pipelines, rate-limiting triggers, 401 unauthorized rejections, 500 error boundary handling, and database failure failovers.
   * **In-Memory Fixture Isolation**: Tests run against a transient, thread-isolated SQLite in-memory database (`StaticPool`) using fixture dependency overrides, eliminating network socket hangs and cross-test state leaks.
2. **Docker Build & Health Check Job**:
   * Builds the multi-stage image.
   * Boots the database and application containers via Docker Compose.
   * Verifies automatic Alembic migration execution on boot.
   * Runs an end-to-end integration smoke test verifying `/health`, asserting authenticated `POST /leads` returns `201`, confirming unauthenticated access returns `401`, and scraping Prometheus `/metrics`.

---

## API Reference

### Public Probes (No Auth Required)
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Live system readiness and database connection probe |
| `GET` | `/metrics` | Prometheus metrics scrape target |

### Protected Endpoints (`X-API-Key` Required)
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/leads` | Validate, sanitize, and persist a new inbound lead |
| `GET` | `/leads` | Filtered, paginated list of leads |
| `GET` | `/leads/{id}` | Retrieve individual lead by primary key |
| `PATCH`| `/leads/{id}` | Partially update lead fields |
| `DELETE`| `/leads/{id}`| Remove lead record (returns `204 No Content`) |

---

## Local Development & Setup

### Prerequisites
* Docker Engine 24+ & Docker Compose v2+
* Python 3.12+

### Quickstart (Docker Compose)
```bash
# Clone the repository
git clone [https://github.com/rahuldegra1/rahuldegra1.git](https://github.com/rahuldegra1/rahuldegra1.git)
cd rahuldegra1

# Boot services (PostgreSQL + FastAPI + Migrations)
docker compose up --build -d

# Check service health
curl -f http://localhost:8000/health
```

### Local Testing & Linting
```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Run Ruff linter and formatter
ruff check .
ruff format --check .

# Run the 14-test integration suite
pytest -v
```

---

## Retrospective & Engineering Trade-offs

* **SQLite vs. PostgreSQL in CI**: We opted for in-memory SQLite (`sqlite:///:memory:`) using SQLAlchemy's `StaticPool` for the Pytest suite. This allows 14 integration tests to execute in under 0.6 seconds without external network dependencies, while delegating full PostgreSQL integration testing to the subsequent Docker Compose container smoke step.
* **Dependency Isolation**: Custom fixtures in `tests/conftest.py` ensure both authenticated and unauthenticated `TestClient` sessions explicitly override `get_db`. Without this, unauthenticated probes would attempt real TCP handshakes against production connection strings during unit testing, hanging test runner sockets.
* **Next Production Optimizations**:
  * Multi-worker process management via Gunicorn with `UvicornWorker` to balance CPU-bound Pydantic validation across multi-core nodes.
  * Engine connection pool pre-pinging (`pool_pre_ping=True`) to drop stale database sockets across idle periods.