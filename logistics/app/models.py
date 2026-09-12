from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ListingSelection(BaseModel):
    listing_id: str
    quantity_kg: float = Field(..., gt=0)


class ListingProduce(BaseModel):
    listing_id: str
    farmer_id: str
    farmer_name: str
    fpo_id: str
    crop: str
    quality: str
    available_quantity_kg: float
    price_per_kg: float
    lat: float
    lon: float


class AggregationRequest(BaseModel):
    crop: str
    requested_quantity_kg: float = Field(..., gt=0)
    selected_listings: list[ListingSelection]

    @model_validator(mode='after')
    def validate_selection(self) -> 'AggregationRequest':
        if not self.selected_listings:
            raise ValueError('At least one listing must be selected.')
        return self


class BulkOrderItem(BaseModel):
    crop: str
    required_quantity_kg: float = Field(..., gt=0)


class BulkOrderMatchRequest(BaseModel):
    buyer_order_id: str
    items: list[BulkOrderItem]

    @model_validator(mode='after')
    def validate_items(self) -> 'BulkOrderMatchRequest':
        if not self.items:
            raise ValueError('At least one crop item must be requested.')
        return self


class PickupLocation(BaseModel):
    farmer_id: str
    farmer_name: str
    quantity_kg: float = Field(..., gt=0)
    lat: float
    lon: float


class Depot(BaseModel):
    lat: float
    lon: float


class RouteOptimizationRequest(BaseModel):
    order_id: str
    vehicle_capacity_kg: float = Field(..., gt=0)
    depot: Depot
    stops: list[PickupLocation]



class RouteStop(BaseModel):
    sequence: int
    farmer_id: str
    farmer_name: str
    quantity_kg: float
    lat: float
    lon: float


class RouteResult(BaseModel):
    order_id: str
    optimized_stop_sequence: list[RouteStop]
    farmer_ids: list[str]
    farmer_names: list[str]
    pickup_quantities: list[float]
    total_quantity_kg: float
    total_road_distance_km: float
    estimated_travel_time_minutes: float
    vehicle_capacity_kg: float
    route_status: Literal['optimized', 'partial', 'pending']


class TransportationCostRequest(BaseModel):
    order_id: str
    distance_km: float = Field(..., gt=0)
    fuel_efficiency_km_l: float = Field(..., gt=0)
    fuel_price_per_l: float = Field(..., ge=0)
    driver_cost: float = Field(..., ge=0)
    toll_cost: float = Field(..., ge=0)
    additional_cost: float = Field(..., ge=0)


class TransportationCostResult(BaseModel):
    order_id: str
    fuel_used_l: float
    fuel_cost: float
    driver_cost: float
    toll_cost: float
    additional_cost: float
    total_estimated_cost: float
    estimate_note: str


class FarmerCostShare(BaseModel):
    farmer_id: str
    farmer_name: str
    quantity_kg: float
    share_percentage: float
    allocated_cost: float


class FarmerCostAllocationRequest(BaseModel):
    order_id: str
    farmer_contributions: list[dict[str, Any]]
    total_transportation_cost: float = Field(..., ge=0)


class AllocationResult(BaseModel):
    order_id: str
    total_transportation_cost: float
    farmer_allocations: list[FarmerCostShare]
