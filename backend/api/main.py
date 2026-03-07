"""
FastAPI Application Entry Point.
Main application initialization with middleware and routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings
from database import init_db, close_db
from api.routes import teacher, student, admin, zalo
from utils.logger import logger

# Persistent directory for uploaded submission images
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads" / "submissions"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Vinschool AI Backend...")
    await init_db()
    logger.info("Database initialized.")

    # Start Google Chat Pub/Sub listener (if configured)
    gchat_listener = None
    if settings.GOOGLE_CLOUD_PROJECT_ID and settings.GOOGLE_CHAT_PUBSUB_SUBSCRIPTION:
        try:
            from services.chat import get_google_chat_listener

            gchat_listener = get_google_chat_listener()
            gchat_listener.start()
            logger.info("Google Chat Pub/Sub listener started.")
        except Exception as e:
            logger.warning(f"Google Chat listener not started: {e}")

    # Start daily summary scheduler
    from services.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down Vinschool AI Backend...")
    scheduler.stop()
    if gchat_listener:
        gchat_listener.stop()
        logger.info("Google Chat Pub/Sub listener stopped.")
    await close_db()
    logger.info("Database connections closed.")


# Create FastAPI app
app = FastAPI(
    title="Vinschool AI Educational Support System",
    description="Multi-agent AI system for educational support",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(teacher.router, prefix="/api/teacher", tags=["Teacher"])
app.include_router(student.router, prefix="/api/student", tags=["Student"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(zalo.router, prefix="/api/zalo", tags=["Zalo"])

# Serve uploaded submission images as static files
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR.parent)),
    name="uploads",
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Vinschool AI Educational Support System",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {"status": "healthy"}
