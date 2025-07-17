import logging
import time
from typing import Optional
from datetime import datetime, timedelta
import requests

from config.settings import AZURE_CONFIG


logger = logging.getLogger(__name__)
class AzureAuthService:
    def __init__(self):
        self.token_cache = {}
        self.token_expiry = None
        self.app_start_time = time.time()
    
    async def get_access_token(self) -> Optional[str]:
        """Get access token using client credentials flow"""
        if self.token_cache and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token_cache.get('access_token')
        
        if not all([AZURE_CONFIG['tenant_id'], AZURE_CONFIG['client_id'], AZURE_CONFIG['client_secret']]):
            logger.error("Missing Azure AD configuration")
            return None
        
        token_url = f"https://login.microsoftonline.com/{AZURE_CONFIG['tenant_id']}/oauth2/v2.0/token"
        
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': AZURE_CONFIG['client_id'],
            'client_secret': AZURE_CONFIG['client_secret'],
            'scope': AZURE_CONFIG['scope']
        }
        
        try:
            response = requests.post(token_url, data=token_data, timeout=10)
            response.raise_for_status()
            
            token_response = response.json()
            self.token_cache = token_response
            
            expires_in = token_response.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logger.info("Successfully obtained Azure AD access token")
            return token_response.get('access_token')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    async def validate_token(self, token: str) -> bool:
        """Validate the provided token"""
        if not token:
            return False
        
        try:
            current_token = await self.get_access_token()
            return token == current_token
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False
