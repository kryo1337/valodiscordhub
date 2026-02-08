import httpx
import os
from typing import Optional, Dict, Any, Union
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

API_BASE_URL = os.getenv("API_BASE_URL")
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN")

APIResponse = Dict[str, Any]
RequestParams = Optional[Dict[str, Any]]
RequestBody = Dict[str, Any]


class APIClient:
    def __init__(self) -> None:
        self.base_url: str = API_BASE_URL
        self.headers: Dict[str, str] = {"Authorization": f"Bot {BOT_API_TOKEN}"}

    async def get(self, endpoint: str, params: RequestParams = None) -> APIResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    params=params,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                if status == 429:
                    raise ValueError("Too many requests. Please try again shortly.")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")

    async def post(self, endpoint: str, data: RequestBody) -> APIResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 409:
                    raise ValueError(f"Resource already exists: {endpoint}")
                if status == 429:
                    raise ValueError("Too many requests. Please try again shortly.")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")

    async def patch(self, endpoint: str, data: RequestBody) -> APIResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                if status == 429:
                    raise ValueError("Too many requests. Please try again shortly.")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")

    async def put(self, endpoint: str, data: RequestBody) -> APIResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                if status == 429:
                    raise ValueError("Too many requests. Please try again shortly.")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")

    async def delete(self, endpoint: str) -> APIResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                if status == 429:
                    raise ValueError("Too many requests. Please try again shortly.")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")


api_client: APIClient = APIClient()
