# Solution 1: Standard FastAPI import (most common)

# Solution 2: If above doesn't work, try Starlette directly
from starlette.middleware.base import BaseHTTPMiddleware

# Solution 3: Alternative - Use FastAPI's built-in middleware decorator
from fastapi import FastAPI, Request, Response
import time
import logging

logger = logging.getLogger(__name__)

from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
        
        return response


# Method 3: Using FastAPI's @app.middleware decorator (Alternative approach)
app = FastAPI()

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Request started: {request.method} {request.url.path} from {client_ip}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} Time: {process_time:.4f}s")
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Method 4: Manual middleware class without BaseHTTPMiddleware
class CustomLoggingMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Create a custom send function to intercept response
            async def custom_send(message):
                if message["type"] == "http.response.start":
                    process_time = time.time() - start_time
                    logger.info(f"Response sent in {process_time:.4f}s")
                await send(message)
            
            # Log request
            logger.info(f"Request: {scope['method']} {scope['path']}")
            
            await self.app(scope, receive, custom_send)
        else:
            await self.app(scope, receive, send)

# Method 5: Check what's available in fastapi.middleware
try:
    import fastapi.middleware
    print("Available in fastapi.middleware:", dir(fastapi.middleware))
except ImportError:
    print("fastapi.middleware not found")

# Method 6: Force import and check FastAPI version
try:
    import fastapi
    print(f"FastAPI version: {fastapi.__version__}")
    
    # Try to access the middleware
    from fastapi import middleware
    print("Middleware module contents:", dir(middleware))
    
except Exception as e:
    print(f"Error: {e}")

# Exam