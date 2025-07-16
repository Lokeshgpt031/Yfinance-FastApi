# services/nse_service.py

from datetime import datetime, timedelta
from pathlib import Path
from nse import NSE
from concurrent.futures import ThreadPoolExecutor

class NseService:
    def __init__(self):
        self.dir = Path(__file__).resolve().parent
        self.nse = NSE(download_folder=self.dir)

    def get_market_status(self):
        try:
            return self.nse.status()
        finally:
            self.nse.exit()

    def get_announcements(self, symbols: list[str], days: int = 1):
        from_date = datetime.now() - timedelta(days=days)
        to_date = datetime.now()

        def fetch_announcement(symbol):
            try:
                data = self.nse.announcements('equities', symbol, from_date=from_date, to_date=to_date)
                return {
                    "symbol": symbol,
                    "data": data,
                    "TimeGenerated": (
                        datetime.strptime(data[0]["sort_date"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                        if data else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                }
            except Exception as e:
                return {"symbol": symbol, "error": str(e), "TimeGenerated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        try:
            with ThreadPoolExecutor() as executor:
                results = list(executor.map(fetch_announcement, symbols))
        finally:
            self.nse.exit()

        return [r for r in results if len(r['data'])!=0]

