from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from datetime import datetime

from config.settings import settings
from controllers import stock_controller, market_controller, broker_controller,nse_controller
from middleware.logging_middleware import LoggingMiddleware
from services.market_service import MarketService
from utils.exceptions import StockAPIException
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
MarketService.initialize_csv()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Comprehensive stock market data API with threading support",
    version=settings.app_version,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Add custom logging middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(stock_controller.router)
app.include_router(market_controller.router)
app.include_router(broker_controller.router)
app.include_router(nse_controller.router)

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

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Real-time stock prices",
            "Historical data",
            "Company information",
            "Financial statements",
            "Dividend history",
            "Stock splits",
            "Analyst recommendations",
            "Earnings data",
            "Multiple stocks support",
            "Threading for performance",
            "Caching system",
            "Market indices",
            "Stock search"
        ],
        "endpoints": {
            "stock_data": [
                "/stock/{symbol}/price",
                "/stock/{symbol}/info",
                "/stock/{symbol}/history",
                "/stock/{symbol}/financials",
                "/stock/{symbol}/dividends",
                "/stock/{symbol}/splits",
                "/stock/{symbol}/recommendations",
                "/stock/{symbol}/earnings",
                "/stock/multiple"
            ],
            "market_data": [
                "/market/trending",
                "/market/indices",
                "/market/search"
            ],
            "documentation": [
                "/docs",
                "/redoc"
            ]
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
        "uptime": "active"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
    