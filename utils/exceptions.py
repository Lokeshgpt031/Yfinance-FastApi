from fastapi import HTTPException
from typing import Optional

class StockAPIException(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class InvalidSymbolException(StockAPIException):
    def __init__(self, symbol: str):
        super().__init__(
            message=f"Invalid ticker symbol: {symbol}",
            status_code=400,
            error_code="INVALID_SYMBOL"
        )

class DataNotFoundException(StockAPIException):
    def __init__(self, symbol: str, data_type: str):
        super().__init__(
            message=f"No {data_type} data found for symbol: {symbol}",
            status_code=404,
            error_code="DATA_NOT_FOUND"
        )

class RateLimitException(StockAPIException):
    def __init__(self):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )

class TimeoutException(StockAPIException):
    def __init__(self):
        super().__init__(
            message="Request timeout. Please try again.",
            status_code=408,
            error_code="REQUEST_TIMEOUT"
        )

