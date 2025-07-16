# routes/nse.py

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from services.nse_service import NseService
from datetime import datetime

router = APIRouter(prefix="/nse",  tags=["NSE Data"])

@router.get("/nseMarket")
def get_nse_market_status():
    service = NseService()
    status = service.get_market_status()
    return JSONResponse(content=status)


@router.get("/api/announcement/{name}")
def get_announcement(name: str, days: int = 1):
    service = NseService()
    names = [n.strip() for n in name.split(",") if n.strip()]
    data = service.get_announcements(names, days=days)

    return JSONResponse(content={
        "status": "success",
        "data": data,
        "TimeGenerated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
