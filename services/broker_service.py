# %%
import os
import pandas as pd
import pyotp
from dotenv import load_dotenv
from NorenRestApiPy.NorenApi import NorenApi
from dhanhq import dhanhq
from services.stock_service import StockService
import numpy as np
load_dotenv()

class BrokerService:
    def __init__(self):
        self.stock_service = StockService()
            

    def fetch_holdings(self):
        totp = pyotp.TOTP(os.getenv('SECRET_TOTP'))
        factor2 = totp.now()

        api = NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        api.login(
            userid=os.getenv('USER'),
            password=os.getenv('U_PWD'),
            twoFA=factor2,
            vendor_code=os.getenv('VC'),
            api_secret=os.getenv('APP_KEY'),
            imei=os.getenv('IMET')
        )

        dhan = dhanhq(client_id=os.getenv('CLIENT_ID'), access_token=os.getenv('DHAN_ACCESS_TOKEN'))
        shoonya_holdings = api.get_holdings()
        dhan_holdings = dhan.get_holdings()['data']

        holdings = []
        for item in shoonya_holdings:
            exch_data = item['exch_tsym'][0]
            holdings.append({
                "exchange": exch_data['exch'],
                "tradingSymbol": exch_data['tsym'].split("-")[0],
                "securityId": exch_data['token'],
                "availableQty": item['npoadqty'],
                "totalQty": item['npoadqty'],
                "isin": exch_data['isin'],
                "avgCostPrice": item['upldprc'],
                "brokerName": "shoonya"
            })

        holdings.extend(dhan_holdings)

        df = pd.DataFrame(holdings)

        # Ensure expected columns are present
        expected_cols = [
            'exchange', 'tradingSymbol', 'securityId',
            'availableQty', 'totalQty', 'isin',
            'avgCostPrice', 'brokerName'
        ]
        df = df.reindex(columns=expected_cols)

        # Fill missing values with appropriate defaults
        df['exchange'] = df['exchange'].fillna("UNKNOWN")
        df['tradingSymbol'] = df['tradingSymbol'].fillna("UNKNOWN")
        df['securityId'] = df['securityId'].fillna("NA")
        df['availableQty'] = df['availableQty'].fillna(0)
        df['totalQty'] = df['totalQty'].fillna(0)
        df['isin'] = df['isin'].fillna("NA")
        df['avgCostPrice'] = df['avgCostPrice'].fillna(0.0)
        df['brokerName'] = df['brokerName'].fillna("dhan")

        # Generate quotes
        BOList = ['INDIGRID']
        df['quote'] = df.apply(
            lambda row: f"{row['tradingSymbol']}.NS" if row['exchange'] in ['NSE', 'ALL'] and row['tradingSymbol'] not in BOList else f"{row['tradingSymbol']}.BO",
            axis=1
        )

        # Replace any remaining NaN with None before JSON conversion
        df = df.replace({np.nan: None})

        return df


    async def get_enriched_holdings(self):
        df = self.fetch_holdings()
        quotes = df['quote'].tolist()

        # Fetch multiple stock prices and company info concurrently
        stock_price_map = await self.stock_service.get_multiple_stocks(quotes)
        company_info_response = await self.stock_service.get_multiple_company_info(quotes)

        # Convert response to dictionary for easy lookup
        company_info_map = {
            list(item.keys())[0]: list(item.values())[0]
            for item in company_info_response.stocks
        }

        enriched = []
        for _, row in df.iterrows():
            quote = row['quote']
            base_data = row.to_dict()

            price_data = next((s for s in stock_price_map['trending_stocks'] if s['symbol'] == quote), {})
            info_data = company_info_map.get(quote, {})

            base_data['price'] = price_data
            base_data['info'] = info_data
            enriched.append(base_data)

        return enriched



