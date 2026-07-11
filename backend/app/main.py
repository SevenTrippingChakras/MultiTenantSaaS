import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import register_rate_limiting
from app.routes import auth, chat, sessions

configure_logging(settings.log_level)
logger = logging.getLogger("aichat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MongoDB on startup, close it on shutdown."""
    await db.connect()
    logger.info("Connected to MongoDB Atlas (db=%s)", db.get_db().name)
    yield
    await db.close()
    logger.info("MongoDB connection closed")


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

register_error_handlers(app)


@app.get("/health")
async def health():
    """Liveness check. Confirms the app is up."""
    return {"status": "ok"}
