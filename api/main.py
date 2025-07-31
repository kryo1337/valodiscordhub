import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import time
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

app = FastAPI(title="ValoDiscordHub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT = 60
RATE_PERIOD = 60
rate_limit_cache = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = int(time.time())
        window = now // RATE_PERIOD
        key = f"{ip}:{window}"
        count = rate_limit_cache.get(key, 0)
        if count >= RATE_LIMIT:
            return Response("Too Many Requests", status_code=429)
        rate_limit_cache[key] = count + 1
        response = await call_next(request)
        if "server" in response.headers:
            del response.headers["server"]
        return response

app.add_middleware(RateLimitMiddleware)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

from routes.players import router as players_router
from routes.leaderboard import router as leaderboard_router
from routes.matches import router as matches_router
from routes.admin import router as admin_router
from routes.queue import router as queue_router
from routes.preferences import router as preferences_router
from auth import router as auth_router

app.include_router(players_router)
app.include_router(leaderboard_router)
app.include_router(matches_router)
app.include_router(admin_router)
app.include_router(queue_router)
app.include_router(preferences_router)
app.include_router(auth_router)
