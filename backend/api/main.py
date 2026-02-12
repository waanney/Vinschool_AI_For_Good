"""
FastAPI Application Entry Point.
Main application initialization with middleware and routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import init_db, close_db
from api.routes import teacher, student, admin, zalo
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Vinschool AI Backend...")
    await init_db()
    logger.info("Database initialized.")

    yield

    # Shutdown
    logger.info("Shutting down Vinschool AI Backend...")
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
