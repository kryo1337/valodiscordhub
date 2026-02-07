"""
ValoDiscordHub API - Main application entry point.
"""

import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError

# Import configuration first (validates env vars on import)
from config import settings

# Import modules
from db import get_db, init_indexes, close_db, check_connection
from rate_limit import check_rate_limit, get_rate_limit_remaining, close_redis
from logging_config import setup_logging, get_logger
from exceptions import (
    ValoHubException,
    valohub_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

# Setup logging
logger = setup_logging("INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting ValoDiscordHub API...")

    # Initialize database indexes
    try:
        await init_indexes()
        logger.info("Database indexes initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database indexes: {e}")

    # Verify database connection
    if await check_connection():
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection check failed")

    logger.info("ValoDiscordHub API started successfully")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down ValoDiscordHub API...")

    # Close database connection
    await close_db()

    # Close Redis connection
    await close_redis()

    logger.info("ValoDiscordHub API shut down gracefully")


app = FastAPI(
    title="ValoDiscordHub API",
    description="API for ValoDiscordHub matchmaking platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis or in-memory fallback."""

    async def dispatch(self, request: Request, call_next):
        # Check for bot token - bypass rate limiting for bot
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bot "):
            token = auth_header[4:]
            if token == settings.bot_api_token:
                response = await call_next(request)
                if "server" in response.headers:
                    del response.headers["server"]
                return response

        # Apply rate limiting for other requests
        client_ip = request.client.host if request.client else "unknown"
        allowed, count = await check_rate_limit(client_ip)

        if not allowed:
            remaining = await get_rate_limit_remaining(client_ip)
            return Response(
                content='{"error": true, "message": "Too many requests. Please slow down and try again later.", "retry_after": 60}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(settings.rate_limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(settings.rate_period),
                    "Retry-After": str(settings.rate_period),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = await get_rate_limit_remaining(client_ip)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests."""

    async def dispatch(self, request: Request, call_next):
        import time

        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms"
        )

        return response


# Add middlewares (order matters - last added is executed first)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Add exception handlers
app.add_exception_handler(ValoHubException, valohub_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/healthz")
async def health_check():
    """Health check endpoint for container orchestration."""
    db_healthy = await check_connection()
    return {
        "status": "ok" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "ValoDiscordHub API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz",
    }


# Import and include routers
from routes.players import router as players_router
from routes.leaderboard import router as leaderboard_router
from routes.matches import router as matches_router
from routes.admin import router as admin_router
from routes.queue import router as queue_router
from routes.preferences import router as preferences_router
from routes.stats import router as stats_router
from routes.history import router as history_router
from auth import router as auth_router

app.include_router(players_router)
app.include_router(leaderboard_router)
app.include_router(matches_router)
app.include_router(admin_router)
app.include_router(queue_router)
app.include_router(preferences_router)
app.include_router(stats_router)
app.include_router(history_router)
app.include_router(auth_router)
