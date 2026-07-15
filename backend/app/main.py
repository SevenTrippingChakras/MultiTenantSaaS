import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db, redis_client, task_queue
from app.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import register_rate_limiting
from app.routes import auth, chat, sessions, usage

configure_logging(settings.log_level)
logger = logging.getLogger("aichat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MongoDB and Redis on startup, close them on shutdown."""
    await db.connect()
    logger.info("Connected to MongoDB Atlas (db=%s)", db.get_db().name)
    await redis_client.connect()
    logger.info("Connected to Redis")
    await task_queue.connect()
    logger.info("Connected to ARQ task queue")
    yield
    await task_queue.close()
    await redis_client.close()
    await db.close()
    logger.info("MongoDB, Redis, and task-queue connections closed")


app = FastAPI(title="AIchat API", lifespan=lifespan)

register_rate_limiting(app)

# Allowed browser origins come from config (CORS_ORIGINS, comma-separated).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

# Added last so it is the outermost middleware: the request id is assigned first.
app.add_middleware(RequestContextMiddleware)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(usage.router)

register_error_handlers(app)


@app.get("/health")
async def health():
    """Liveness check. Confirms the app process is up (no dependencies touched)."""
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness check. Pings Mongo and Redis; 503 if either is unreachable.

    Orchestrators use this to decide whether to route traffic here (distinct
    from /health liveness, which only says the process is alive).
    """
    checks = {}
    for name, ping in (("mongo", _ping_mongo), ("redis", _ping_redis)):
        try:
            await ping()
            checks[name] = "ok"
        except Exception:
            logger.exception("Readiness check failed for %s", name)
            checks[name] = "error"

    ok = all(v == "ok" for v in checks.values())
    status = 200 if ok else 503
    return JSONResponse(
        status_code=status,
        content={"status": "ok" if ok else "error", "checks": checks},
    )


async def _ping_mongo() -> None:
    await db.get_db().command("ping")


async def _ping_redis() -> None:
    await redis_client.get_redis().ping()
