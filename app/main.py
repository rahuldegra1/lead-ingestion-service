from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.logging_config import logger
from app.middleware import ObservabilityMiddleware
from app.rate_limiter import limiter
from app.routers import leads


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Application starting up...")
    yield
    logger.info("Graceful shutdown: closing SQLAlchemy connection pools...")
    engine.dispose()
    logger.info("Database connections closed cleanly.")


app = FastAPI(
    title="Lead Ingestion Service",
    version="1.0.0",
    description="Microservice for validating, storing, and filtering inbound sales leads.",
    lifespan=lifespan,
)

# Attach limiter to FastAPI application state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", tags=["Observability"]
)

# Register custom observability middleware
app.add_middleware(ObservabilityMiddleware)

# Include endpoint router
app.include_router(leads.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"Unhandled application error: {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please reference the request ID when contacting support.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "lead-ingestion",
            "database": "connected",
        }
    except Exception as exc:
        logger.error(f"Readiness probe failed: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "lead-ingestion",
                "database": "disconnected",
                "error": "Database unreachable",
            },
        )
