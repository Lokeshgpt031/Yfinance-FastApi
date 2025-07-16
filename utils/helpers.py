import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import yfinance as yf
from utils.exceptions import InvalidSymbolException, DataNotFoundException
import logging

logger = logging.getLogger(__name__)

def get_ticker(symbol: str) -> yf.Ticker:
    """Get yfinance ticker object with error handling"""
    try:
        ticker = yf.Ticker(symbol)
        # Test if ticker is valid by trying to get info
        info = ticker.info
        if not info or info.get('symbol') is None:
            raise InvalidSymbolException(symbol)
        return ticker
    except Exception as e:
        logger.error(f"Error getting ticker for {symbol}: {str(e)}")
        raise InvalidSymbolException(symbol)

def df_to_dict(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert DataFrame to list of dictionaries"""
    if df.empty:
        return []
    try:
        df_reset = df.reset_index()
        # Convert timestamps to strings for JSON serialization
        for col in df_reset.columns:
            if df_reset[col].dtype == 'datetime64[ns]':
                df_reset[col] = df_reset[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        return df_reset.to_dict('records')
    except Exception as e:
        logger.error(f"Error converting DataFrame to dict: {str(e)}")
        return []

def validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol"""
    if not symbol or not isinstance(symbol, str):
        raise InvalidSymbolException(symbol)
    return symbol.strip().upper()

def safe_get(dictionary: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary"""
    try:
        return dictionary.get(key, default)
    except (AttributeError, KeyError):
        return default

def format_price(price: Optional[float]) -> Optional[float]:
    """Format price to 2 decimal places"""
    if price is None:
        return None
    try:
        return round(float(price), 2)
    except (ValueError, TypeError):
        return None

def calculate_change(current: float, previous: float) -> tuple:
    """Calculate price change and percentage change"""
    if previous == 0:
        return 0.0, 0.0
    
    change = current - previous
    change_percent = (change / previous) * 100
    
    return round(change, 2), round(change_percent, 2)
