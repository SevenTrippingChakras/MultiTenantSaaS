import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected errors and return a clean JSON 500 (no stack trace leak)."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    """Liveness check. Confirms the app is up."""
    return {"status": "ok"}
