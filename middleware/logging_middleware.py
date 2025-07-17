
import logging
from starlette.middleware.base import BaseHTTPMiddleware

import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log incoming request
        logger.info(f"🔵 REQUEST: {request.method} {request.url.path} from {client_ip}")
        logger.info(f"   Headers: Authorization: {'***' if 'authorization' in request.headers else 'None'}")
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            status_emoji = "✅" if response.status_code < 400 else "❌"
            logger.info(f"{status_emoji} RESPONSE: {request.method} {request.url.path} "
                       f"Status: {response.status_code} Time: {process_time:.4f}s")
            
            # Add processing time to response headers
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"❌ ERROR: {request.method} {request.url.path} "
                        f"Error: {str(e)} Time: {process_time:.4f}s")
            raise