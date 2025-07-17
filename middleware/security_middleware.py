from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Enter your bearer token"
)

class SecurityMiddleWare(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude docs and openapi endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json","/","/health",'/api/auth/token']:
            return await call_next(request)
        # Apply security for all other endpoints
        try:
            credentials: HTTPAuthorizationCredentials = await security(request)
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "message": "Authentication credentials were not provided or invalid",
                    "detail": str(e)
                }
            )
        # Optional: Verify token here
        response = await call_next(request)
        return response
