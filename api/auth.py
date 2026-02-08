"""
Authentication and authorization module.
Provides JWT authentication for web users and bot token authentication for the Discord bot.
"""

from fastapi import Depends, HTTPException, status, Request, APIRouter
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
import httpx
from typing import Optional, Literal
from config import settings

# Origin type for event deduplication
EventOrigin = Literal["bot", "frontend"]

# OAuth URLs
OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
OAUTH_USER_URL = "https://discord.com/api/users/@me"

router = APIRouter(prefix="/auth", tags=["auth"])


def get_request_origin(request: Request) -> EventOrigin:
    """
    Determine the origin of a request based on the Authorization header.
    Returns "bot" if Bot token is used, "frontend" otherwise.
    This is used for WebSocket event deduplication.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bot "):
        return "bot"
    return "frontend"


async def require_bot_token(request: Request) -> None:
    """
    Dependency that requires a valid bot token.
    Used for endpoints that should only be accessible by the Discord bot.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bot "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bot token. This endpoint requires Bot authentication.",
        )
    token = auth[4:]
    if token != settings.bot_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot token"
        )


async def get_current_user(request: Request) -> dict:
    """
    Dependency that requires a valid JWT token.
    Returns the decoded user payload from the JWT.
    Used for endpoints that require an authenticated web user.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to access this resource",
        )
    token = auth[7:]
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
        )


async def optional_current_user(request: Request) -> Optional[dict]:
    """
    Dependency that optionally validates a JWT token.
    Returns the user payload if a valid JWT is provided, None otherwise.
    Used for endpoints that can be accessed by both authenticated and anonymous users,
    but may show different data based on authentication status.
    """
    auth = request.headers.get("Authorization")
    if not auth:
        return None

    # Check for bot token first (bot can access everything)
    if auth.startswith("Bot "):
        token = auth[4:]
        if token == settings.bot_api_token:
            # Return a special bot user payload
            return {"discord_id": "bot", "username": "ValoHub Bot", "is_bot": True}
        return None

    # Check for JWT bearer token
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            payload["is_bot"] = False
            return payload
        except JWTError:
            return None

    return None


async def require_auth(request: Request) -> dict:
    """
    Dependency that requires either bot token or JWT.
    Used for endpoints accessible by both the bot and authenticated web users.
    """
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid token.",
        )

    # Check for bot token
    if auth.startswith("Bot "):
        token = auth[4:]
        if token == settings.bot_api_token:
            return {"discord_id": "bot", "username": "ValoHub Bot", "is_bot": True}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot token"
        )

    # Check for JWT
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            payload["is_bot"] = False
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token. Please log in again.",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authorization header format",
    )


@router.get("/login")
def login():
    """Redirect to Discord OAuth login page."""
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify email",
        "prompt": "consent",
    }
    url = OAUTH_AUTHORIZE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: Optional[str] = None):
    """Handle Discord OAuth callback and issue JWT."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    async with httpx.AsyncClient() as client:
        data = {
            "client_id": settings.discord_client_id,
            "client_secret": settings.discord_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.discord_redirect_uri,
            "scope": "identify email",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_resp = await client.post(OAUTH_TOKEN_URL, data=data, headers=headers)
        token_json = token_resp.json()
        access_token = token_json.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Failed to get access token from Discord. Please try again.",
            )

        user_resp = await client.get(
            OAUTH_USER_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        user_json = user_resp.json()

        jwt_token = jwt.encode(
            {
                "discord_id": user_json["id"],
                "username": user_json["username"],
                "email": user_json.get("email"),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        return {"jwt": jwt_token, "user": user_json}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user
