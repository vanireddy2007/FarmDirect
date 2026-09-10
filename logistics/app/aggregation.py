from __future__ import annotations

from datetime import datetime, timezone

from .data import AggregationBatch, INITIAL_LISTINGS


class AggregationStore:
    def __init__(self) -> None:
        self.listings = {listing.listing_id: listing for listing in INITIAL_LISTINGS}
        self.batches: dict[str, AggregationBatch] = {}
        self.batch_counter = 1

    def get_available_produce(self, fpo_id: str) -> list[dict]:
        return [
            {
                'listing_id': listing.listing_id,
                'farmer_id': listing.farmer_id,
                'farmer_name': listing.farmer_name,
                'fpo_id': listing.fpo_id,
                'crop': listing.crop,
                'quality': listing.quality,
                'available_quantity_kg': listing.available_quantity_kg,
                'price_per_kg': listing.price_per_kg,
                'latitude': listing.latitude,
                'longitude': listing.longitude,
            }
            for listing in self.listings.values()
            if listing.fpo_id == fpo_id and listing.available_quantity_kg > 0
        ]

    def validate_fpo(self, fpo_id: str) -> bool:
        return any(listing.fpo_id == fpo_id for listing in self.listings.values())

    def create_batch(self, fpo_id: str, crop: str, requested_quantity_kg: float, selections: list[dict]) -> dict:
        if not self.validate_fpo(fpo_id):
            raise ValueError(f'Invalid FPO ID: {fpo_id}')

        total_selected = 0.0
        contributions: list[dict] = []
        for selection in selections:
            listing_id = selection['listing_id']
            quantity = float(selection['quantity_kg'])
            if quantity <= 0:
                raise ValueError(f'Quantity for listing {listing_id} must be greater than zero.')
            listing = self.listings.get(listing_id)
            if listing is None or listing.fpo_id != fpo_id:
                raise ValueError(f'Invalid listing {listing_id} for FPO {fpo_id}.')
            if listing.crop.lower() != crop.lower():
                raise ValueError(f'Listing {listing_id} does not match crop {crop}.')
            if quantity > listing.available_quantity_kg:
                raise ValueError(f'Insufficient available quantity for listing {listing_id}.')
            if any(entry['listing_id'] == listing_id for entry in contributions):
                raise ValueError(f'Duplicate allocation detected for listing {listing_id}.')
            total_selected += quantity
            contributions.append({
                'listing_id': listing_id,
                'farmer_id': listing.farmer_id,
                'farmer_name': listing.farmer_name,
                'quantity_kg': quantity,
                'crop': listing.crop,
            })

        if total_selected != requested_quantity_kg:
            raise ValueError('Selected quantities do not match the requested quantity.')

        if total_selected <= 0:
            raise ValueError('Requested quantity must be greater than zero.')

        batch_id = f'BATCH-{self.batch_counter:04d}'
        self.batch_counter += 1
        batch = AggregationBatch(
            batch_id=batch_id,
            fpo_id=fpo_id,
            crop=crop,
            total_quantity_kg=total_selected,
            available_quantity_kg=total_selected,
            farmer_contributions=contributions,
            status='created',
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        for contribution in contributions:
            listing = self.listings[contribution['listing_id']]
            listing.available_quantity_kg -= contribution['quantity_kg']

        self.batches[batch_id] = batch

        return {
            'batch_id': batch_id,
            'fpo_id': fpo_id,
            'crop': crop,
            'total_quantity_kg': total_selected,
            'available_quantity_kg': total_selected,
            'status': 'created',
            'farmer_contributions': contributions,
        }

    def get_batches(self, fpo_id: str) -> list[dict]:
        results = []
        for batch in self.batches.values():
            if batch.fpo_id == fpo_id:
                results.append({
                    'batch_id': batch.batch_id,
                    'crop': batch.crop,
                    'total_quantity_kg': batch.total_quantity_kg,
                    'available_quantity_kg': batch.available_quantity_kg,
                    'farmer_contributions': batch.farmer_contributions,
                    'status': batch.status,
                    'order_association': batch.order_id,
                })
        return results

    def match_bulk_order(self, fpo_id: str, buyer_order_id: str, crop: str, required_quantity_kg: float) -> dict:
        compatible_batches = [
            batch for batch in self.batches.values() if batch.fpo_id == fpo_id and batch.crop.lower() == crop.lower() and batch.available_quantity_kg > 0
        ]
        if not compatible_batches:
            return {'buyer_order_id': buyer_order_id, 'matched_quantity_kg': 0, 'remaining_quantity_kg': required_quantity_kg, 'matched_batches': []}

        matched_batches = []
        remaining = required_quantity_kg
        for batch in compatible_batches:
            if remaining <= 0:
                break
            match_qty = min(batch.available_quantity_kg, remaining)
            if match_qty > 0:
                matched_batches.append({
                    'batch_id': batch.batch_id,
                    'matched_quantity_kg': match_qty,
                    'farmer_contributions': batch.farmer_contributions,
                })
                batch.available_quantity_kg -= match_qty
                batch.order_id = buyer_order_id
                batch.status = 'matched'
                remaining -= match_qty

        return {
            'buyer_order_id': buyer_order_id,
            'matched_quantity_kg': required_quantity_kg - remaining,
            'remaining_quantity_kg': remaining,
            'matched_batches': matched_batches,
        }
