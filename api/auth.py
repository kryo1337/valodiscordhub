import os
from fastapi import Depends, HTTPException, status, Request, APIRouter
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from jose import JWTError, jwt
import httpx
from typing import Optional

load_dotenv()

BOT_API_TOKEN = os.getenv("BOT_API_TOKEN")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"

OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
OAUTH_USER_URL = "https://discord.com/api/users/@me"

router = APIRouter(prefix="/auth", tags=["auth"])

async def require_bot_token(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bot "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bot token")
    token = auth[4:]
    if token != BOT_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot token")

async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing JWT")
    token = auth[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT")

@router.get("/login")
def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify email",
        "prompt": "consent"
    }
    url = OAUTH_AUTHORIZE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)

@router.get("/callback")
async def callback(code: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
            "scope": "identify email"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_resp = await client.post(OAUTH_TOKEN_URL, data=data, headers=headers)
        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        user_resp = await client.get(OAUTH_USER_URL, headers={"Authorization": f"Bearer {access_token}"})
        user_json = user_resp.json()
        jwt_token = jwt.encode({
            "discord_id": user_json["id"],
            "username": user_json["username"],
            "email": user_json.get("email"),
        }, JWT_SECRET, algorithm=JWT_ALGO)
        return {"jwt": jwt_token, "user": user_json}
