import os
from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
import uvicorn
from datetime import datetime
from dotenv import load_dotenv

from middleware.security_middleware import SecurityMiddleWare
load_dotenv()
 
from config.settings import settings
from controllers import auth_controller, home_controller, stock_controller, market_controller, broker_controller,nse_controller
from middleware.logging_middleware import LoggingMiddleware
from services.market_service import MarketService
from utils.exceptions import StockAPIException
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Initialize FastAPI app
# bearer_scheme = HTTPBearer()

# Configure OAuth2 for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="aapi/uth/token",
    description="Enter your access token"
)

# Alternative: HTTP Bearer for header-based auth
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Enter your bearer token"
)
secured_router = APIRouter(dependencies=[Depends(security)])
# secured_router = APIRouter(
#     dependencies=[Depends(verify_token)]
# )


app = FastAPI(
    title="Stock Market API",
    description="""
**Authentication**
- All authenticated endpoints require a Bearer token.
- Example: `Bearer abc12345`
- Click 'Authorize' and enter your token (omit 'Bearer').
    """,

)

@app.get("/secure")
def secure_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return {"token": credentials.credentials}
# Register secured endpoints
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Add custom logging middleware
app.include_router(secured_router)
app.include_router(auth_controller.router, prefix="/api") 
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleWare)
MarketService.initialize_csv()
# Include routers
app.include_router(stock_controller.router,prefix="/api",dependencies=[Depends(security)])
app.include_router(market_controller.router,prefix="/api",dependencies=[Depends(security)])
app.include_router(broker_controller.router,prefix="/api",dependencies=[Depends(security)])
app.include_router(nse_controller.router,prefix="/api",dependencies=[Depends(security)])
app.include_router(auth_controller.router,prefix="/api")
app.include_router(home_controller.router)

# Global exception handler
@app.exception_handler(StockAPIException)
async def stock_api_exception_handler(request, exc: StockAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": datetime.now().isoformat()
        }
    )



# if __name__ == "__main__":
#     import uvicorn
#     def run_server():
#         uvicorn.run(
#         "main:app",
#         host=settings.host,
#         port=settings.port,
#         reload=settings.debug,
#         log_level="info"
#             )
#     # run_server()
#     server_thread = threading.Thread(target=run_server)
#     server_thread.start()
#     server_thread.join()

if __name__ == "__main__":
    # Validate configuration
    required_env_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Please set the following environment variables:")
        for var in missing_vars:
            logger.info(f"  export {var}='your-value'")
        exit(1)
    
    logger.info("Starting FastAPI Stock Market API with Azure AD authentication")
    logger.info("API Documentation available at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
    

    
