"""AgentID FastAPI application — entry point."""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.middleware.rate_limit import limiter
from app.routers import agents, credentials, audit, verify
from app.services.jwt_service import ensure_keys

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("agentid_startup", version=settings.version, env=settings.environment)
    ensure_keys()
    await init_db()
    yield
    logger.info("agentid_shutdown")


app = FastAPI(
    title="AgentID",
    description="Verifiable identity for every AI agent",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


# Routers
app.include_router(agents.router, prefix="/v1")
app.include_router(credentials.router, prefix="/v1")
app.include_router(audit.router, prefix="/v1")
app.include_router(verify.router, prefix="/v1")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "environment": settings.environment,
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "name": "AgentID",
        "tagline": "Verifiable identity for every AI agent",
        "version": settings.version,
        "docs": "/docs",
    }
