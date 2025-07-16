from fastapi import APIRouter, HTTPException, Query, Depends
import logging

from models.schemas import CompanyInfoSchema, TrendingStocksResponse, SearchResponse
from services.market_service import MarketService
from utils.exceptions import StockAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market Data"])

# Dependency to get market service
def get_market_service() -> MarketService:
    return MarketService()

@router.get("/trending", response_model=TrendingStocksResponse)
async def get_trending_stocks(
    market_service: MarketService = Depends(get_market_service)
):
    """Get trending stocks data"""
    try:
        result = await market_service.get_trending_stocks()
        return TrendingStocksResponse(**result)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_trending_stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/indices")
async def get_market_indices(
    market_service: MarketService = Depends(get_market_service)
):
    """Get market indices data"""
    try:
        return await market_service.get_market_indices()
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_market_indices: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/search", response_model=CompanyInfoSchema)
async def search_stock(
    query: str = Query(..., min_length=1, description="Search term for stock name or symbol"),
    market_service: MarketService = Depends(get_market_service)
):
    """Search stocks by name or symbol"""
    try:
        result = await market_service.search_stock(query)
        return result
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in search_stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
