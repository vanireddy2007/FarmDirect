from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FarmerListing:
    listing_id: str
    farmer_id: str
    farmer_name: str
    fpo_id: str
    crop: str
    quality: str
    available_quantity_kg: float
    price_per_kg: float
    latitude: float
    longitude: float


@dataclass
class AggregationBatch:
    batch_id: str
    fpo_id: str
    crop: str
    total_quantity_kg: float
    available_quantity_kg: float
    farmer_contributions: list[dict] = field(default_factory=list)
    status: str = 'created'
    order_id: str | None = None
    created_at: str | None = None


INITIAL_LISTINGS: list[FarmerListing] = [
    FarmerListing('L001', 'F001', 'Farmer A', 'FPO-001', 'Rice', 'Grade A', 800.0, 28.0, 25.010, 91.020),
    FarmerListing('L002', 'F002', 'Farmer B', 'FPO-001', 'Rice',  'Grade A', 600.0, 27.5, 25.030, 91.040),
    FarmerListing('L003', 'F003', 'Farmer C', 'FPO-001', 'Wheat', 'Grade B', 700.0, 26.0, 25.050, 91.060),
    FarmerListing('L004', 'F004', 'Farmer D', 'FPO-002', 'Rice', 'Grade A', 900.0, 29.0, 24.900, 91.200),
    FarmerListing('L005', 'F005', 'Farmer E', 'FPO-001', 'Potato', 'Grade A', 500.0, 18.0, 25.070, 91.080),
]

FPO_IDS = {'FPO-001', 'FPO-002'}
