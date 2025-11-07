"""Asynchronous IPTVPortal client with async context management."""
import httpx
import asyncio
from typing import Optional, Any, List
from iptvportal.config import IPTVPortalSettings
from iptvportal.auth import AsyncAuthManager
from iptvportal.query.builder import QueryBuilder
from iptvportal.exceptions import IPTVPortalError, APIError, TimeoutError, ConnectionError

class AsyncIPTVPortalClient:
    """
    Asynchronous IPTVPortal API client, supports 'async with' and parallel execution.
    """
    def __init__(self, settings: Optional[IPTVPortalSettings] = None, **kwargs):
        self.settings = settings or IPTVPortalSettings(**kwargs)
        self.auth = AsyncAuthManager(self.settings)
        self.query = QueryBuilder()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None
    async def __aenter__(self):
        await self.connect()
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    async def connect(self):
        self._http_client = httpx.AsyncClient(
            timeout=self.settings.timeout,
            verify=self.settings.verify_ssl,
            http2=True,
        )
        self._session_id = await self.auth.authenticate(self._http_client)
    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            self._session_id = None
    async def execute(self, query: dict[str, Any]) -> Any:
        if not self._http_client or not self._session_id:
            raise IPTVPortalError("Async client not connected. Use 'async with' statement or call connect().")
        headers = {
            "Iptvportal-Authorization": f"sessionid={self._session_id}",
            "Content-Type": "application/json"
        }
        last_error = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = await self._http_client.post(
                    self.settings.api_url,
                    json=query,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    raise APIError(
                        data["error"].get("message", "API error"),
                        details=data["error"],
                    )
                return data.get("result")
            except httpx.TimeoutException as e:
                last_error = TimeoutError(f"Request timeout: {e}")
            except httpx.ConnectError as e:
                last_error = ConnectionError(f"Connection failed: {e}")
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    raise APIError(f"Client error: {e}")
                last_error = APIError(f"HTTP error: {e}")
            except Exception as e:
                last_error = IPTVPortalError(f"Unexpected error: {e}")
            if attempt < self.settings.max_retries:
                delay = self.settings.retry_delay * (2 ** attempt)
                if self.settings.log_requests:
                    print(f"Async retry {attempt + 1}/{self.settings.max_retries}, waiting {delay}s ...")
                await asyncio.sleep(delay)
        raise last_error
    async def execute_many(self, queries: List[dict[str, Any]]) -> List[Any]:
        tasks = [self.execute(query) for query in queries]
        return await asyncio.gather(*tasks)
