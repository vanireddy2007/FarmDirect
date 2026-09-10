from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from .data import AggregationBatch, INITIAL_LISTINGS


class AggregationStore:
    def __init__(self) -> None:
        self.listings = {
            listing.listing_id: listing
            for listing in deepcopy(INITIAL_LISTINGS)
        }
        self.batches: dict[str, AggregationBatch] = {}
        self.batch_counter = 1

    def score_listing_for_bulk_order(
        self,
        listing,
        required_quantity_kg: float,
        reference_latitude: float,
        reference_longitude: float,
    ) -> float:
        """Return the weighted suitability score for one compatible listing."""
        breakdown = self.get_listing_score_breakdown(
            listing,
            required_quantity_kg,
            reference_latitude,
            reference_longitude,
        )
        return breakdown['score']

    @staticmethod
    def _quality_score(quality: str) -> float | None:
        """Return a deterministic quality score, or ``None`` for an unknown grade."""
        quality_scores = {
            'grade a': 100.0,
            'a': 100.0,
            'premium': 100.0,
            'grade b': 75.0,
            'b': 75.0,
            'standard': 75.0,
            'grade c': 50.0,
            'c': 50.0,
            'basic': 50.0,
        }
        return quality_scores.get(quality.strip().lower())

    def get_listing_score_breakdown(
        self,
        listing,
        required_quantity_kg: float,
        reference_latitude: float,
        reference_longitude: float,
    ) -> dict[str, float]:
        """Calculate transparent 0-100 component scores and their weighted total.

        Quality compatibility is worth 25%, price competitiveness 20%, quantity
        fit 20%, pickup proximity 20%, route compatibility 10%, and fulfillment
        reliability 5%. Route and reliability are neutral (50/100) because the
        MVP has no route or reliability data; they are not inferred from other
        fields.
        """
        if required_quantity_kg <= 0:
            raise ValueError('Requested quantity must be greater than zero.')

        # Price score: lower price gets a higher score.
        all_prices = [
            item.price_per_kg
            for item in self.listings.values()
            if item.crop.lower() == listing.crop.lower()
            and item.available_quantity_kg > 0
            and self._quality_score(item.quality) is not None
        ]

        if all_prices:
            min_price = min(all_prices)
            max_price = max(all_prices)

            if max_price == min_price:
                # No price difference is evidence of neither advantage nor
                # disadvantage, so keep this factor neutral.
                price_score = 50.0
            else:
                price_score = (
                    (max_price - listing.price_per_kg)
                    / (max_price - min_price)
                ) * 100
        else:
            price_score = 0.0

        quality_score = self._quality_score(listing.quality)
        if quality_score is None:
            raise ValueError(f'Listing {listing.listing_id} has incompatible quality.')

        # Quantity score: listings that contribute more useful quantity toward
        # the buyer requirement receive a higher score.
        quantity_ratio = min(
            listing.available_quantity_kg / required_quantity_kg,
            1.0,
        )
        quantity_score = quantity_ratio * 100

        # Distance score: closer pickup points are preferred.
        lat_diff = listing.latitude - reference_latitude
        lon_diff = listing.longitude - reference_longitude

        distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

        # Normalize distance into a simple proximity score.
        distance_score = max(0.0, 100.0 - (distance * 1000))

        # No route or fulfillment history exists in the MVP, so both factors
        # are deliberately neutral instead of being guessed from listing data.
        route_score = 50.0
        reliability_score = 50.0

        # Weighted suitability score using the business weights above.
        score = (
            quality_score * 0.25
            + price_score * 0.20
            + quantity_score * 0.20
            + distance_score * 0.20
            + route_score * 0.10
            + reliability_score * 0.05
        )

        return {
            'quality': round(quality_score, 2),
            'price': round(price_score, 2),
            'quantity': round(quantity_score, 2),
            'distance': round(distance_score, 2),
            'route': route_score,
            'reliability': reliability_score,
            'score': round(score, 2),
        }

    def get_suitability_scores(
        self,
        fpo_id: str,
        crop: str,
        required_quantity_kg: float,
        reference_latitude: float,
        reference_longitude: float,
    ) -> list[dict]:
        """Rank currently available, quality-compatible listings for an order."""
        if required_quantity_kg <= 0:
            raise ValueError('Requested quantity must be greater than zero.')

        candidates = []
        for listing in self.listings.values():
            if (
                listing.fpo_id != fpo_id
                or listing.crop.lower() != crop.lower()
                or listing.available_quantity_kg <= 0
                or self._quality_score(listing.quality) is None
            ):
                continue

            breakdown = self.get_listing_score_breakdown(
                listing,
                required_quantity_kg,
                reference_latitude,
                reference_longitude,
            )
            candidates.append({
                'listing_id': listing.listing_id,
                'farmer_id': listing.farmer_id,
                'farmer_name': listing.farmer_name,
                'crop': listing.crop,
                'quality': listing.quality,
                'available_quantity_kg': listing.available_quantity_kg,
                'price_per_kg': listing.price_per_kg,
                'suitability_score': breakdown['score'],
                'score_breakdown': {
                    key: breakdown[key]
                    for key in ('quality', 'price', 'quantity', 'distance', 'route', 'reliability')
                },
            })

        return sorted(
            candidates,
            key=lambda candidate: candidate['suitability_score'],
            reverse=True,
        )

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
