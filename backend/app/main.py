import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.core.errors import register_error_handlers
from app.routes import auth, chat, sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
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

# Allow the Vite dev server (frontend) to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)

register_error_handlers(app)


@app.get("/health")
async def health():
    """Liveness check. Confirms the app is up."""
    return {"status": "ok"}
