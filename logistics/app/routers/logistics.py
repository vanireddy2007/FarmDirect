from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..logistics import FarmerCostAllocator, OSRMService, RoutingOptimizer, TransportationCostCalculator
from ..models import (
    FarmerCostAllocationRequest,
    RouteOptimizationRequest,
    TransportationCostRequest,
)

router = APIRouter(prefix='/api/logistics', tags=['Logistics'])
optimizer = RoutingOptimizer(OSRMService())
route_store: dict[str, dict] = {}


@router.post('/optimize-route')
async def optimize_route(request: RouteOptimizationRequest):
    try:
        result = await optimizer.optimize_route(request)
        route_store[request.order_id] = result.model_dump()
        return result.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (TimeoutError, ConnectionError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post('/calculate-cost')
def calculate_cost(request: TransportationCostRequest):
    result = TransportationCostCalculator.calculate(request)
    return result.model_dump()


@router.post('/allocate-cost')
def allocate_cost(request: FarmerCostAllocationRequest):
    try:
        result = FarmerCostAllocator.allocate(request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get('/routes/{order_id}')
def get_route(order_id: str):
    if order_id not in route_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Route not found for the supplied order ID.')
    return route_store[order_id]
