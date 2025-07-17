import asyncio
import concurrent.futures
from typing import Optional, List, Dict, Any
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.schemas import (
    MultipleInfoResponse, StockPriceSchema, CompanyInfoSchema, HistoricalDataSchema,
    FinancialsSchema, DividendsSchema, StockSplitSchema,
    RecommendationSchema, EarningsSchema
)
from models.enums import Period, Interval
from utils.helpers import get_ticker, df_to_dict, validate_symbol, safe_get, format_price, calculate_change
from utils.exceptions import DataNotFoundException, TimeoutException
from config.settings import settings

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=settings.max_workers)
        self.cache = {}  # Simple in-memory cache
        self.cache_timeout = settings.cache_timeout

    def _get_cache_key(self, symbol: str, data_type: str, **kwargs) -> str:
        """Generate cache key"""
        key_parts = [symbol, data_type]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return data
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        """Set data in cache with timestamp"""
        self.cache[key] = (data, datetime.now())

    def _fetch_stock_data(self, symbol: str, schema_required: bool = False) -> Any:
        """Fetch stock data from yfinance. Return schema or dict based on flag."""
        ticker = get_ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="5d" if schema_required else "2d")

        if hist.empty:
            raise DataNotFoundException(symbol, "price")

        current_price = float(hist['Close'].iloc[-1])
        previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
        change, change_percent = calculate_change(current_price, previous_close)

        if schema_required:
            return StockPriceSchema(
                symbol=symbol,
                current_price=format_price(current_price),
                previous_close=format_price(previous_close),
                change=change,
                change_percent=change_percent,
                volume=int(hist['Volume'].iloc[-1]),
                market_cap=safe_get(info, 'marketCap'),
                day_high=format_price(safe_get(info, 'dayHigh')),
                day_low=format_price(safe_get(info, 'dayLow')),
                fifty_two_week_high=format_price(safe_get(info, 'fiftyTwoWeekHigh')),
                fifty_two_week_low=format_price(safe_get(info, 'fiftyTwoWeekLow'))
            )
        else:
            return {
                'symbol': symbol,
                'name': safe_get(info, 'longName', safe_get(info, 'shortName', '')),
                'current_price': format_price(current_price),
                'change': change,
                'change_percent': change_percent,
                'volume': int(hist['Volume'].iloc[-1]),
                'market_cap': safe_get(info, 'marketCap'),
                'sector': safe_get(info, 'sector')
            }

    async def get_stock_price(self, symbol: str) -> StockPriceSchema:
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "price")
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, self._fetch_stock_data, symbol, True)
            result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
            self._set_cache(cache_key, result)
            return result
        except asyncio.TimeoutError:
            raise TimeoutException()
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            raise

    async def get_multiple_stocks(self, symbols: List[str]) -> Dict[str, Any]:
        validated_symbols = [validate_symbol(symbol) for symbol in symbols]

        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(self.executor, self._safe_fetch_stock_data, symbol)
            for symbol in validated_symbols
        ]

        results = await asyncio.gather(*futures, return_exceptions=True)

        trending_stocks = [
            result for result in results
            if isinstance(result, dict) and 'error' not in result
        ]

        trending_stocks.sort(key=lambda x: x.get('market_cap', 0) or 0, reverse=True)

        return {
            'trending_stocks': trending_stocks,
            'total_stocks': len(trending_stocks),
            'market_status': 'active'
        }

    def _safe_fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        try:
            return self._fetch_stock_data(symbol, schema_required=False)
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    def _fetch_company_info(self, symbol: str) -> CompanyInfoSchema:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return CompanyInfoSchema(
                symbol=symbol,
                name=safe_get(info, "longName", safe_get(info, "shortName", "")),
                sector=info.get("sector"),
                industry=info.get("industry"),
                country=info.get("country"),
                website=info.get("website"),
                business_summary=info.get("longBusinessSummary"),
                market_cap=info.get("marketCap"),
                employees=info.get("fullTimeEmployees"),
                dividend_yield=info.get("dividendYield"),
                pe_ratio=info.get("trailingPE"),
                beta=info.get("beta"),
                revenue=info.get("totalRevenue"),
                profit_margin=info.get("profitMargins"),
                bookValue=info.get("bookValue"),
                priceToBook=info.get("priceToBook"),
                quickRatio=info.get("quickRatio"),
                debtToEquity=info.get("debtToEquity"),
            )
        except Exception as e:
            logger.error(f"Failed to fetch company info for {symbol}: {str(e)}")
            return CompanyInfoSchema(
                symbol=symbol,
                name="",
                business_summary=f"Error: {str(e)}"
            )

    async def get_company_info(self, symbol: str) -> Dict[str, Any]:
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "company_info")
        
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(self.executor, self._fetch_company_info, symbol)
        result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
        
        # Convert CompanyInfoSchema to dict for caching and return
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.__dict__
        self._set_cache(cache_key, result_dict)
        return result_dict

    async def get_multiple_company_info(self, symbols: List[str]) -> MultipleInfoResponse:
        validated = [validate_symbol(s) for s in symbols]
        
        loop = asyncio.get_event_loop()
        tasks = []
        
        for symbol in validated:
            cache_key = self._get_cache_key(symbol, "company_info")
            cached = self._get_from_cache(cache_key)
            if cached:
                # Create a coroutine that returns the cached result
                async def return_cached(cached_data=cached):
                    return cached_data
                tasks.append(return_cached())
            else:
                task = loop.run_in_executor(self.executor, self._fetch_company_info, symbol)
                tasks.append(asyncio.wait_for(task, timeout=settings.timeout_seconds))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        stocks: List[Dict[str, CompanyInfoSchema]] = []
        success_count = 0
        failure_count = 0
        
        for symbol, res in zip(validated, results):
            try:
                if isinstance(res, CompanyInfoSchema):
                    # Direct schema object from _fetch_company_info
                    stocks.append({symbol: res})
                    success_count += 1
                    # Cache the result
                    result_dict = res.model_dump() if hasattr(res, 'model_dump') else res.__dict__
                    self._set_cache(self._get_cache_key(symbol, "company_info"), result_dict)
                elif isinstance(res, dict):
                    # Cached result - convert to schema
                    schema = CompanyInfoSchema(**res)
                    stocks.append({symbol: schema})
                    success_count += 1
                elif isinstance(res, Exception):
                    # Exception occurred
                    error_schema = CompanyInfoSchema(
                        symbol=symbol,
                        name="",
                        business_summary=f"Error: {str(res)}"
                    )
                    stocks.append({symbol: error_schema})
                    failure_count += 1
                else:
                    # Unexpected result type
                    error_schema = CompanyInfoSchema(
                        symbol=symbol,
                        name="",
                        business_summary=f"Error: Unexpected result type: {type(res)}"
                    )
                    stocks.append({symbol: error_schema})
                    failure_count += 1
            except Exception as e:
                # Error processing result
                error_schema = CompanyInfoSchema(
                    symbol=symbol,
                    name="",
                    business_summary=f"Error processing result: {str(e)}"
                )
                stocks.append({symbol: error_schema})
                failure_count += 1
        
        return MultipleInfoResponse(
            stocks=stocks,
            total_stocks=len(symbols),
            successful_requests=success_count,
            failed_requests=failure_count
        )

    async def get_historical_data(self, symbol: str, period: Period, interval: Interval) -> HistoricalDataSchema:
        """Get historical stock data"""
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "history", period=period.value, interval=interval.value)
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        def _fetch_history():
            try:
                ticker = get_ticker(symbol)
                hist = ticker.history(period=period.value, interval=interval.value)
                
                if hist.empty:
                    raise DataNotFoundException(symbol, "historical data")
                
                data = df_to_dict(hist)
                
                historical_data = HistoricalDataSchema(
                    symbol=symbol,
                    period=period.value,
                    interval=interval.value,
                    data=data,
                    data_count=len(data)
                )
                
                return historical_data
                
            except Exception as e:
                logger.error(f"Error fetching history for {symbol}: {str(e)}")
                raise

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, _fetch_history)
            result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
            
            self._set_cache(cache_key, result)
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutException()

    async def get_financials(self, symbol: str) -> FinancialsSchema:
        """Get financial statements"""
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "financials")
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        def _fetch_financials():
            try:
                ticker = get_ticker(symbol)

                def safe_df_to_dict(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
                    if df is None or df.empty:
                        return None
                    return {
                        str(index): {str(k): v for k, v in row.items()}
                        for index, row in df.T.iterrows()
                    }

                financials = FinancialsSchema(
                    symbol=symbol,
                    quarterly_financials=safe_df_to_dict(ticker.quarterly_financials),
                    yearly_financials=safe_df_to_dict(ticker.financials),
                    balance_sheet=safe_df_to_dict(ticker.balance_sheet),
                    cash_flow=safe_df_to_dict(ticker.cashflow),
                )

                return financials

            except Exception as e:
                logger.error(f"Error fetching financials for {symbol}: {str(e)}")
                raise


        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, _fetch_financials)
            result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
            
            self._set_cache(cache_key, result)
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutException()


    async def get_dividends(self, symbol: str) -> DividendsSchema:
        """Get dividend data"""
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "dividends")
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        def _fetch_dividends():
            try:
                ticker = get_ticker(symbol)
                dividends = ticker.dividends
                
                dividend_data = df_to_dict(dividends.to_frame('dividend'))
                
                dividends_schema = DividendsSchema(
                    symbol=symbol,
                    dividends=dividend_data,
                    total_dividends=len(dividend_data)
                )
                
                return dividends_schema
                
            except Exception as e:
                logger.error(f"Error fetching dividends for {symbol}: {str(e)}")
                raise

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, _fetch_dividends)
            result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
            
            self._set_cache(cache_key, result)
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutException()

    async def get_splits(self, symbol: str) -> StockSplitSchema:
        """Get stock split data"""
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "splits")
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        def _fetch_splits():
            try:
                ticker = get_ticker(symbol)
                splits = ticker.splits
                
                split_data = df_to_dict(splits.to_frame('split_ratio'))
                
                splits_schema = StockSplitSchema(
                    symbol=symbol,
                    splits=split_data,
                    total_splits=len(split_data)
                )
                
                return splits_schema
                
            except Exception as e:
                logger.error(f"Error fetching splits for {symbol}: {str(e)}")
                raise

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, _fetch_splits)
            result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
            
            self._set_cache(cache_key, result)
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutException()

    async def get_recommendations(self, symbol: str) -> RecommendationSchema:
        """Get analyst recommendations"""
        symbol = validate_symbol(symbol)
        cache_key = self._get_cache_key(symbol, "recommendations")
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        def _fetch_recommendations():
            try:
                ticker = get_ticker(symbol)
                recommendations = ticker.recommendations
                
                recommendation_data = df_to_dict(recommendations) if recommendations is not None else []
                
                recommendations_schema = RecommendationSchema(
                    symbol=symbol,
                    recommendations=recommendation_data
                )
                
                return recommendations_schema
                
            except Exception as e:
                logger.error(f"Error fetching recommendations for {symbol}: {str(e)}")
                raise

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, _fetch_recommendations)
            result = await asyncio.wait_for(future, timeout=settings.timeout_seconds)
            
            self._set_cache(cache_key, result)
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutException()

    async def get_market_indices(self) -> Dict[str, Any]:
        """Get market indices data"""
        
        def _fetch_index(symbol: str):
            try:
                ticker = get_ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="2d")
                
                if hist.empty:
                    return None
                
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change, change_percent = calculate_change(current_price, previous_close)
                
                index_name = {
                    '^GSPC': 'S&P 500',
                    '^DJI': 'Dow Jones',
                    '^IXIC': 'NASDAQ'
                }.get(symbol, symbol)
                
                return {
                    'symbol': symbol,
                    'name': index_name,
                    'current_price': format_price(current_price),
                    'change': change,
                    'change_percent': change_percent,
                    'volume': int(hist['Volume'].iloc[-1])
                }
                
            except Exception as e:
                logger.error(f"Error fetching index {symbol}: {str(e)}")
                return None

        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(self.executor, _fetch_index, symbol)
            for symbol in self.market_indices
        ]
        
        try:
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            indices = []
            for result in results:
                if result and not isinstance(result, Exception):
                    indices.append(result)
            
            return {
                'market_indices': indices,
                'total_indices': len(indices)
            }
            
        except Exception as e:
            logger.error(f"Error in get_market_indices: {str(e)}")
            raise

    async def search_stocks(self, query: str) -> Dict[str, Any]:
        """Search stocks by name or symbol"""
        query_lower = query.lower()
        
        # Extended stock database for search
        stock_database = {
            'AAPL': 'Apple Inc.',
            'GOOGL': 'Alphabet Inc.',
            'MSFT': 'Microsoft Corporation',
            'AMZN': 'Amazon.com Inc.',
            'TSLA': 'Tesla Inc.',
            'META': 'Meta Platforms Inc.',
            'NVDA': 'NVIDIA Corporation',
            'NFLX': 'Netflix Inc.',
            'BABA': 'Alibaba Group Holding Ltd.',
            'DIS': 'The Walt Disney Company',
            'PYPL': 'PayPal Holdings Inc.',
            'ADBE': 'Adobe Inc.',
            'CRM': 'Salesforce Inc.',
            'INTC': 'Intel Corporation',
            'AMD': 'Advanced Micro Devices Inc.',
            'ORCL': 'Oracle Corporation',
            'IBM': 'International Business Machines Corporation',
            'UBER': 'Uber Technologies Inc.',
            'LYFT': 'Lyft Inc.',
            'SPOT': 'Spotify Technology S.A.',
            'TWTR': 'Twitter Inc.',
            'SNAP': 'Snap Inc.',
            'ZM': 'Zoom Video Communications Inc.',
            'SLACK': 'Slack Technologies Inc.',
            'SQ': 'Square Inc.',
            'SHOP': 'Shopify Inc.'
        }
        
        results = []
        
        for symbol, name in stock_database.items():
            if (query_lower in symbol.lower() or 
                query_lower in name.lower() or
                any(query_lower in word.lower() for word in name.split())):
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'match_score': self._calculate_match_score(query_lower, symbol, name)
                })
        
        # Sort by match score (descending)
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Remove match_score from final results
        for result in results:
            del result['match_score']
        
        return {
            'search_results': results[:20],  # Limit to top 20 results
            'total_results': len(results),
            'query': query
        }

    def _calculate_match_score(self, query: str, symbol: str, name: str) -> float:
        """Calculate match score for search results"""
        score = 0.0
        
        # Exact symbol match gets highest score
        if query == symbol.lower():
            score += 100
        elif query in symbol.lower():
            score += 50
        
        # Exact name match
        if query == name.lower():
            score += 90
        elif query in name.lower():
            score += 30
        
        # Word match in name
        name_words = name.lower().split()
        for word in name_words:
            if query in word:
                score += 20
            elif word.startswith(query):
                score += 15
        
        return score

    def __del__(self):
        """Cleanup executor on service destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
