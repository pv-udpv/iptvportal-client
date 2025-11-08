"""Synchronous IPTVPortal client with context manager and resource support."""
from typing import Optional, Any
import httpx
from iptvportal.config import IPTVPortalSettings
from iptvportal.auth import AuthManager
from iptvportal.query.builder import QueryBuilder
from iptvportal.exceptions import IPTVPortalError, APIError, TimeoutError, ConnectionError

class IPTVPortalClient:
    """
    Synchronous IPTVPortal API client.
    Use as context manager for automatic connection management.
    """
    def __init__(self, settings: Optional[IPTVPortalSettings] = None, **kwargs):
        self.settings = settings or IPTVPortalSettings(**kwargs)
        self.auth = AuthManager(self.settings)
        self.query = QueryBuilder()
        self._http_client: Optional[httpx.Client] = None
        self._session_id: Optional[str] = None
    def __enter__(self):
        self.connect()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    def connect(self):
        self._http_client = httpx.Client(
            timeout=self.settings.timeout,
            verify=self.settings.verify_ssl,
            http2=True,
        )
        self._session_id = self.auth.authenticate(self._http_client)
    def close(self):
        if self._http_client:
            self._http_client.close()
            self._http_client = None
            self._session_id = None
    def execute(self, query: dict[str, Any]) -> Any:
        if not self._http_client or not self._session_id:
            raise IPTVPortalError("Client not connected. Use 'with' statement or call connect().")
        headers = {
            "Iptvportal-Authorization": f"sessionid={self._session_id}",
            "Content-Type": "application/json"
        }
        import time
        last_error = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self._http_client.post(
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
                # Try to get response body for better error messages
                try:
                    error_body = e.response.text
                    error_json = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else None
                    
                    if error_json and "error" in error_json:
                        error_msg = f"HTTP {e.response.status_code}: {error_json['error'].get('message', str(e))}"
                    elif error_body:
                        error_msg = f"HTTP {e.response.status_code}: {error_body[:500]}"  # Limit body length
                    else:
                        error_msg = f"HTTP {e.response.status_code}: {e}"
                except Exception:
                    error_msg = f"HTTP {e.response.status_code}: {e}"
                
                if 400 <= e.response.status_code < 500:
                    raise APIError(error_msg)
                last_error = APIError(error_msg)
            except Exception as e:
                last_error = IPTVPortalError(f"Unexpected error: {e}")
            if attempt < self.settings.max_retries:
                delay = self.settings.retry_delay * (2 ** attempt)
                if self.settings.log_requests:
                    print(f"Retry attempt {attempt + 1}/{self.settings.max_retries}, waiting {delay}s...")
                time.sleep(delay)
        raise last_error
