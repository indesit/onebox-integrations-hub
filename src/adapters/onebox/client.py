"""OneBox API v2 Client (HUB-009)."""

import os
import httpx
from src.core.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

class OneBoxClient:
    def __init__(self, domain: str, login: str, token: str):
        self.base_url = f"{domain}/api/v2/"
        self.login = login
        self.api_password = token
        self._current_token = None

    def _get_token(self) -> str:
        """Fetch a fresh session token using login and restapipassword."""
        if self._current_token:
            return self._current_token
            
        url = f"{self.base_url}token/get/"
        payload = {
            "login": self.login,
            "restapipassword": self.api_password
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == 1:
                    self._current_token = data["dataArray"]["token"]
                    return self._current_token
                else:
                    logger.error("onebox_auth_failed", response=data)
                    raise ValueError(f"OneBox Auth Failed: {data}")
        except Exception as e:
            logger.error("onebox_auth_exception", error=str(e))
            raise

    def create_order(self, payload: list[dict]) -> dict:
        """Calls POST /api/v2/order/set/ with order data."""
        return self._post_with_retry("order/set/", payload)

    def set_products(self, payload: list[dict]) -> dict:
        """Calls POST /api/v2/product/set/ to upsert products."""
        return self._post_with_retry("product/set/", payload)

    def set_contacts(self, payload: list[dict]) -> dict:
        """Calls POST /api/v2/contact/set/ to create/update contacts."""
        return self._post_with_retry("contact/set/", payload)

    def get_contacts(self, payload: dict) -> dict:
        """Calls POST /api/v2/contact/get/ to search for contacts."""
        return self._post_with_retry("contact/get/", payload)

    def _post_with_retry(self, endpoint: str, payload: list | dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        
        # Try up to 2 times (once with current token, once with a fresh one if expired)
        for attempt in range(2):
            token = self._get_token()
            headers = {
                "token": token,
                "Content-Type": "application/json"
            }
            
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check for token expiry
                    if data.get("status") == 0 and any("token" in str(err).lower() for err in data.get("errorArray", [])):
                        logger.warning("onebox_token_expired_retrying")
                        self._current_token = None # Force refresh on next loop
                        continue
                    
                    return data
            except Exception as e:
                logger.error("onebox_api_error", error=str(e), url=url)
                return {"status": 0, "errorArray": [str(e)]}
                
        return {"status": 0, "errorArray": ["Token refresh failed or max retries exceeded"]}

# Global instance
onebox_client = OneBoxClient(
    domain=os.getenv("ONEBOX_DOMEN", ""),
    login=os.getenv("ONEBOX_LOGIN", ""),
    token=os.getenv("ONEBOX_TOKEN", "") # This is the REST API Password/Current Token
)
