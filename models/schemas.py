from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from models.enums import DataType, Interval, Period

class BaseResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseResponse):
    success: bool = False
    error_code: str
    details: Optional[str] = None

class StockPriceSchema(BaseModel):
    symbol: str
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None

class CompanyInfoSchema(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    business_summary: Optional[str] = None
    market_cap: Optional[float] = None
    employees: Optional[int] = None
    dividend_yield: Optional[float] = None
    pe_ratio: Optional[float] = None
    beta: Optional[float] = None
    revenue: Optional[float] = None
    profit_margin: Optional[float] = None
    bookValue:Optional[float]=None
    priceToBook:Optional[float]=None
    quickRatio:Optional[float]=None
    debtToEquity:Optional[float]=None

class MultipleInfoResponse(BaseModel):
    stocks: List[Dict[str, CompanyInfoSchema]]
    total_stocks: int
    successful_requests: int
    failed_requests: int
    
class HistoricalDataSchema(BaseModel):
    symbol: str
    period: str
    interval: str
    data: List[Dict[str, Any]]
    data_count: int

class FinancialsSchema(BaseModel):
    symbol: str
    quarterly_financials: Optional[Dict[str, Any]] = None
    yearly_financials: Optional[Dict[str, Any]] = None
    balance_sheet: Optional[Dict[str, Any]] = None
    cash_flow: Optional[Dict[str, Any]] = None

class DividendsSchema(BaseModel):
    symbol: str
    dividends: List[Dict[str, Any]]
    total_dividends: int

class StockSplitSchema(BaseModel):
    symbol: str
    splits: List[Dict[str, Any]]
    total_splits: int

class RecommendationSchema(BaseModel):
    symbol: str
    recommendations: List[Dict[str, Any]]

class EarningsSchema(BaseModel):
    symbol: str
    quarterly_earnings: Optional[Dict[str, Any]] = None
    yearly_earnings: Optional[Dict[str, Any]] = None
    earnings_calendar: Optional[Dict[str, Any]] = None

class MultipleStocksResponse(BaseModel):
    stocks: List[Dict[str, Any]]
    total_stocks: int
    successful_requests: int
    failed_requests: int

class TrendingStocksResponse(BaseModel):
    trending_stocks: List[Dict[str, Any]]
    total_stocks: int
    market_status: str

class SearchResponse(BaseModel):
    search_results: List[Dict[str, Any]]
    total_results: int
    query: str

# Request models
class MultipleStocksRequest(BaseModel):
    symbols: List[str]
    data_types: List[DataType] = [DataType.PRICE]

class HistoricalDataRequest(BaseModel):
    symbol: str
    period: Period = Period.ONE_MONTH
    interval: Interval = Interval.ONE_DAY

