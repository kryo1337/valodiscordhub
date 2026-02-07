"""
Custom exceptions and error handlers for user-friendly error messages.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import logging

logger = logging.getLogger("valohub")


# Custom exception classes
class ValoHubException(Exception):
    """Base exception for ValoHub API."""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class PlayerNotFoundError(ValoHubException):
    """Raised when a player is not found."""

    def __init__(self, discord_id: str = None):
        message = "Player not found"
        if discord_id:
            message = f"Player with ID '{discord_id}' was not found. Make sure they have registered."
        super().__init__(message, status_code=404)


class MatchNotFoundError(ValoHubException):
    """Raised when a match is not found."""

    def __init__(self, match_id: str = None):
        message = "Match not found"
        if match_id:
            message = f"Match '{match_id}' was not found. It may have been deleted or never existed."
        super().__init__(message, status_code=404)


class QueueNotFoundError(ValoHubException):
    """Raised when a queue is not found."""

    def __init__(self, rank_group: str = None):
        message = "Queue not found"
        if rank_group:
            message = f"Queue for rank group '{rank_group}' was not found."
        super().__init__(message, status_code=404)


class LeaderboardNotFoundError(ValoHubException):
    """Raised when a leaderboard is not found."""

    def __init__(self, rank_group: str = None):
        message = "Leaderboard not found"
        if rank_group:
            message = f"Leaderboard for rank group '{rank_group}' was not found. It may not have been initialized yet."
        super().__init__(message, status_code=404)


class DuplicateResourceError(ValoHubException):
    """Raised when attempting to create a duplicate resource."""

    def __init__(self, resource_type: str, identifier: str = None):
        message = f"{resource_type} already exists"
        if identifier:
            message = f"{resource_type} '{identifier}' already exists."
        super().__init__(message, status_code=409)


class AuthenticationError(ValoHubException):
    """Raised for authentication failures."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(ValoHubException):
    """Raised for authorization failures."""

    def __init__(
        self, message: str = "You don't have permission to perform this action"
    ):
        super().__init__(message, status_code=403)


class RateLimitError(ValoHubException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        message = (
            f"Too many requests. Please wait {retry_after} seconds before trying again."
        )
        super().__init__(message, status_code=429, details={"retry_after": retry_after})


class ValidationException(ValoHubException):
    """Raised for validation errors with user-friendly messages."""

    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, details=details)


# Error response model
def create_error_response(status_code: int, message: str, details: dict = None) -> dict:
    """Create a standardized error response."""
    response = {
        "error": True,
        "status_code": status_code,
        "message": message,
    }
    if details:
        response["details"] = details
    return response


# Exception handlers
async def valohub_exception_handler(
    request: Request, exc: ValoHubException
) -> JSONResponse:
    """Handle ValoHub custom exceptions."""
    logger.warning(f"ValoHubException: {exc.message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.status_code, exc.message, exc.details),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions with user-friendly messages."""
    # Map common status codes to user-friendly messages
    user_friendly_messages = {
        400: "The request was invalid. Please check your input and try again.",
        401: "Please log in to access this resource.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource was not found.",
        405: "This action is not allowed.",
        409: "This resource already exists.",
        422: "The provided data was invalid. Please check the format and try again.",
        429: "Too many requests. Please slow down and try again later.",
        500: "An internal error occurred. Please try again later.",
        502: "The server is temporarily unavailable. Please try again later.",
        503: "The service is temporarily unavailable. Please try again later.",
    }

    # Use the exception detail if provided, otherwise use friendly message
    message = (
        exc.detail
        if exc.detail
        else user_friendly_messages.get(
            exc.status_code, "An unexpected error occurred."
        )
    )

    logger.warning(f"HTTPException: {message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.status_code, message),
    )


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with user-friendly messages."""
    errors = exc.errors()

    # Create user-friendly error messages
    messages = []
    for error in errors:
        field = ".".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        messages.append(f"'{field}': {msg}")

    message = "Validation failed: " + "; ".join(messages)

    logger.warning(f"ValidationError: {message}")
    return JSONResponse(
        status_code=422, content=create_error_response(422, message, {"errors": errors})
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            500, "An unexpected error occurred. Our team has been notified."
        ),
    )
