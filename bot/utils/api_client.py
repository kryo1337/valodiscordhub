import httpx
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN")

class APIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.headers = {"Authorization": f"Bot {BOT_API_TOKEN}"}
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    raise ValueError(f"Resource already exists: {endpoint}")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")
    
    async def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Resource not found: {endpoint}")
                raise
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to API: {e}")

api_client = APIClient() 