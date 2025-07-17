from fastapi import APIRouter, HTTPException

from models.schemas import TokenResponse
from services.auth_service import AzureAuthService

azure_auth = AzureAuthService()

router = APIRouter(prefix="/auth", tags=["Auth"])
@router.get("/token", response_model=TokenResponse)
async def get_token():
    """Get Azure AD access token"""
    token = await azure_auth.get_access_token()
    if not token:
        raise HTTPException(
            status_code=500,
            detail="Failed to obtain access token from Azure AD"
        )
    
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=3600
    )