"""
FastAPI application entry point.

Startup sequence:
  1. connect_to_mongodb()       — connect + ping Atlas
  2. (inside connect) ensure collections + indexes + seed default model config
  3. FastAPI app starts accepting requests

Shutdown sequence:
  1. disconnect_from_mongodb()  — close Motor client
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.mongodb import connect_to_mongodb, disconnect_from_mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: handles startup and shutdown.

    connect_to_mongodb() now does all of:
      - connection + ping
      - time-series collection creation
      - all 20+ indexes (idempotent)
      - default ModelConfig seeding
    """
    await connect_to_mongodb()
    yield
    await disconnect_from_mongodb()


app = FastAPI(
    title="AI Camera Platform",
    description=(
        "Real-time AI camera monitoring with YOLOv8 and MongoDB Atlas. "
        "Provides video upload, MJPEG streaming, live analytics, session history, "
        "alerts, and incident management."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
