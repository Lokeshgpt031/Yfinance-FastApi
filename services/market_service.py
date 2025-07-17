import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from services.stock_service import StockService
import yfinance as yf
import requests
import pandas as pd
from models.schemas import CompanyInfoSchema
from utils.helpers import get_ticker, validate_symbol, safe_get, format_price, calculate_change
from config.settings import settings
import os

logger = logging.getLogger(__name__)

class MarketService:
    CSV_PATH = "nse_stocks.csv"
    NSE_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    df = None
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=settings.max_workers)
        self.trending_symbols = [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 
            'BABA', 'DIS', 'PYPL', 'ADBE', 'CRM', 'INTC', 'AMD'
        ]
        self.market_indices = ['^GSPC', '^DJI', '^IXIC']  # S&P 500, Dow Jones, NASDAQ

    @staticmethod
    def initialize_csv():
        print("📥 Downloading NSE stock list...")
        r = requests.get(MarketService.NSE_CSV_URL)
        with open(MarketService.CSV_PATH, "wb") as f:
            f.write(r.content)

        # Load and transform CSV
        raw_df = pd.read_csv(MarketService.CSV_PATH)
        df = raw_df[["Company Name", "Symbol"]].rename(
            columns={"Company Name": "company", "Symbol": "ticker"}
        )
        df["ticker"] = df["ticker"].astype(str) + ".NS"
        df.to_csv(MarketService.CSV_PATH, index=False)
        print("✅ NSE stock list saved.")
        logger.info("initialize_csv is successful")
        MarketService.df = pd.read_csv(MarketService.CSV_PATH)

    @staticmethod
    def find_ticker(query: str):
        query_lower = query.strip().lower()
        df = MarketService.df
        # Exact ticker match
        match = df[df['ticker'].str.lower() == query_lower]
        if not match.empty:
            return match.iloc[0]['ticker']
        # Company name contains
        match = df[df['company'].str.lower().str.contains(query_lower)]
        if not match.empty:
            return match.iloc[0]['ticker']
        return None
    async def search_stock(self,query: str)->CompanyInfoSchema:
        ticker = MarketService.find_ticker(query)
        if not ticker:
            return {"error": "Stock not found."}

        try:
            service=StockService()
            return await service.get_company_info(ticker)
        except Exception as e:
            return {"error": f"yfinance error: {str(e)}"}
        
    async def get_trending_stocks(self) -> Dict[str, Any]:
        """Get trending stocks data using threading"""
        
        def _fetch_trending_stock(symbol: str):
            try:
                ticker = get_ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="2d")
                
                if hist.empty:
                    return None
                
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change, change_percent = calculate_change(current_price, previous_close)
                
                return {
                    'symbol': symbol,
                    'name': safe_get(info, 'longName', safe_get(info, 'shortName', '')),
                    'current_price': format_price(current_price),
                    'change': change,
                    'change_percent': change_percent,
                    'volume': int(hist['Volume'].iloc[-1]),
                    'market_cap': safe_get(info, 'marketCap'),
                    'sector': safe_get(info, 'sector'),
                    'pe_ratio': safe_get(info, 'trailingPE'),
                    'beta': safe_get(info, 'beta')
                }
                
            except Exception as e:
                logger.error(f"Error fetching trending stock {symbol}: {str(e)}")
                return None
        
        # Use ThreadPoolExecutor for parallel processing
        loop = asyncio.get_event_loop()
        
        futures = [
            loop.run_in_executor(self.executor, _fetch_trending_stock, symbol)
            for symbol in self.trending_symbols
        ]
        
        try:
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            trending_stocks = []
            successful_requests = 0
            failed_requests = 0
            
            for result in results:
                if isinstance(result, Exception):
                    failed_requests += 1
                    logger.error(f"Exception in trending stock fetch: {str(result)}")
                elif result is None:
                    failed_requests += 1
                else:
                    successful_requests += 1
                    trending_stocks.append(result)
            
            # Sort by market cap (descending) if available
            trending_stocks.sort(
                key=lambda x: x.get('market_cap', 0) or 0, 
                reverse=True
            )
            
            return {
                'trending_stocks': trending_stocks,
                'total_requested': len(self.trending_symbols),
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error in get_trending_stocks: {str(e)}")
            raise
    
    async def get_market_indices(self) -> Dict[str, Any]:
        """Get market indices data"""
        
        def _fetch_market_index(symbol: str):
            try:
                ticker = get_ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="2d")
                
                if hist.empty:
                    return None
                
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change, change_percent = calculate_change(current_price, previous_close)
                
                # Map symbol to readable name
                name_mapping = {
                    '^GSPC': 'S&P 500',
                    '^DJI': 'Dow Jones',
                    '^IXIC': 'NASDAQ'
                }
                
                return {
                    'symbol': symbol,
                    'name': name_mapping.get(symbol, safe_get(info, 'longName', symbol)),
                    'current_price': format_price(current_price),
                    'change': change,
                    'change_percent': change_percent,
                    'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0
                }
                
            except Exception as e:
                logger.error(f"Error fetching market index {symbol}: {str(e)}")
                return None
        
        loop = asyncio.get_event_loop()
        
        futures = [
            loop.run_in_executor(self.executor, _fetch_market_index, symbol)
            for symbol in self.market_indices
        ]
        
        try:
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            indices = []
            successful_requests = 0
            failed_requests = 0
            
            for result in results:
                if isinstance(result, Exception):
                    failed_requests += 1
                    logger.error(f"Exception in market index fetch: {str(result)}")
                elif result is None:
                    failed_requests += 1
                else:
                    successful_requests += 1
                    indices.append(result)
            
            return {
                'market_indices': indices,
                'total_requested': len(self.market_indices),
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error in get_market_indices: {str(e)}")
            raise
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get complete market overview with trending stocks and indices"""
        try:
            # Fetch both trending stocks and market indices concurrently
            trending_task = self.get_trending_stocks()
            indices_task = self.get_market_indices()
            
            trending_data, indices_data = await asyncio.gather(
                trending_task, 
                indices_task, 
                return_exceptions=True
            )
            
            result = {
                'timestamp': asyncio.get_event_loop().time(),
                'status': 'success'
            }
            
            # Handle trending stocks data
            if isinstance(trending_data, Exception):
                logger.error(f"Error fetching trending stocks: {str(trending_data)}")
                result['trending_stocks'] = {'error': str(trending_data)}
            else:
                result['trending_stocks'] = trending_data
            
            # Handle market indices data
            if isinstance(indices_data, Exception):
                logger.error(f"Error fetching market indices: {str(indices_data)}")
                result['market_indices'] = {'error': str(indices_data)}
            else:
                result['market_indices'] = indices_data
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_market_overview: {str(e)}")
            raise
    
    async def get_single_stock(self, symbol: str) -> Dict[str, Any]:
        """Get single stock data"""
        
        def _fetch_single_stock(symbol: str):
            try:
                # Validate symbol first
                if not validate_symbol(symbol):
                    return {'error': f'Invalid symbol: {symbol}'}
                
                ticker = get_ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="5d")
                
                if hist.empty:
                    return {'error': f'No data available for {symbol}'}
                
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change, change_percent = calculate_change(current_price, previous_close)
                
                return {
                    'symbol': symbol.upper(),
                    'name': safe_get(info, 'longName', safe_get(info, 'shortName', '')),
                    'current_price': format_price(current_price),
                    'change': change,
                    'change_percent': change_percent,
                    'volume': int(hist['Volume'].iloc[-1]),
                    'market_cap': safe_get(info, 'marketCap'),
                    'sector': safe_get(info, 'sector'),
                    'industry': safe_get(info, 'industry'),
                    'pe_ratio': safe_get(info, 'trailingPE'),
                    'beta': safe_get(info, 'beta'),
                    'dividend_yield': safe_get(info, 'dividendYield'),
                    'fifty_two_week_high': safe_get(info, 'fiftyTwoWeekHigh'),
                    'fifty_two_week_low': safe_get(info, 'fiftyTwoWeekLow'),
                    'timestamp': asyncio.get_event_loop().time()
                }
                
            except Exception as e:
                logger.error(f"Error fetching stock {symbol}: {str(e)}")
                return {'error': f'Failed to fetch data for {symbol}: {str(e)}'}
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(self.executor, _fetch_single_stock, symbol)
            return result
            
        except Exception as e:
            logger.error(f"Error in get_single_stock: {str(e)}")
            return {'error': f'Failed to fetch data for {symbol}: {str(e)}'}
    
    def __del__(self):
        """Cleanup executor on service destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)


