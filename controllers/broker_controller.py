from fastapi import APIRouter, Depends
from services.broker_service import BrokerService

router = APIRouter(prefix="/broker", tags=["Broker"])
def get_broker_service() ->  BrokerService:
    return  BrokerService()
@router.get("/holdings")
async def get_broker_holdings(
        broker_service: BrokerService = Depends(get_broker_service)

):
    return await broker_service.get_enriched_holdings()
