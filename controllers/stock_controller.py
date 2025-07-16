from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import logging

from models.schemas import (
    StockPriceSchema, CompanyInfoSchema, HistoricalDataSchema,
    FinancialsSchema, DividendsSchema, StockSplitSchema,
    RecommendationSchema, EarningsSchema, MultipleStocksResponse,
    BaseResponse, ErrorResponse, TrendingStocksResponse
)
from models.enums import Period, Interval, DataType
from services.stock_service import StockService
from utils.exceptions import StockAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stock", tags=["Stock Data"])

# Dependency to get stock service
def get_stock_service() -> StockService:
    return StockService()

@router.get("/{symbol}/price", response_model=StockPriceSchema)
async def get_stock_price(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get current stock price and basic metrics"""
    try:
        return await stock_service.get_stock_price(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_stock_price: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/info", response_model=CompanyInfoSchema)
async def get_company_info(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get detailed company information"""
    try:
        return await stock_service.get_company_info(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_company_info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/multiple_info/{symbol}", response_model=List[CompanyInfoSchema])
async def get_company_info(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get detailed company information"""
    try:
        return await stock_service.get_company_info(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_company_info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/history", response_model=HistoricalDataSchema)
async def get_historical_data(
    symbol: str,
    period: Period = Period.ONE_MONTH,
    interval: Interval = Interval.ONE_DAY,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get historical stock data"""
    try:
        return await stock_service.get_historical_data(symbol, period, interval)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_historical_data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/financials", response_model=FinancialsSchema)
async def get_financials(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get financial statements"""
    try:
        return await stock_service.get_financials(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_financials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/dividends", response_model=DividendsSchema)
async def get_dividends(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get dividend history"""
    try:
        return await stock_service.get_dividends(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_dividends: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/splits", response_model=StockSplitSchema)
async def get_splits(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get stock split history"""
    try:
        return await stock_service.get_splits(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_splits: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}/recommendations", response_model=RecommendationSchema)
async def get_recommendations(
    symbol: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """Get analyst recommendations"""
    try:
        return await stock_service.get_recommendations(symbol)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/multiple_stocks", response_model=TrendingStocksResponse)
async def get_multiple_stocks(
    symbols: str = Query(..., description="Comma-separated stock symbols"),
    stock_service: StockService = Depends(get_stock_service)
):
    """Get data for multiple stocks"""
    try:
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No valid symbols provided")
        
        result = await stock_service.get_multiple_stocks(symbol_list)
        return TrendingStocksResponse(**result)
    except StockAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_multiple_stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
