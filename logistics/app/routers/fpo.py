from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..aggregation import AggregationStore
from ..models import AggregationRequest, BulkOrderMatchRequest

router = APIRouter(prefix='/api/fpo', tags=['FPO'])
storage = AggregationStore()


@router.get('/{fpo_id}/available-produce')
def get_available_produce(fpo_id: str):
    if not storage.validate_fpo(fpo_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'FPO {fpo_id} not found.')
    return {'fpo_id': fpo_id, 'produce': storage.get_available_produce(fpo_id)}


@router.post('/{fpo_id}/aggregate')
def create_aggregation_batch(fpo_id: str, request: AggregationRequest):
    try:
        batch = storage.create_batch(fpo_id, request.crop, request.requested_quantity_kg, [s.model_dump() for s in request.selected_listings])
        return {
    'message': 'Aggregation batch created successfully.',
    'batch': batch,
    'contributions': batch.get('farmer_contributions', [])
}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get('/{fpo_id}/batches')
def get_batches(fpo_id: str):
    if not storage.validate_fpo(fpo_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'FPO {fpo_id} not found.')
    return {'fpo_id': fpo_id, 'batches': storage.get_batches(fpo_id)}


@router.post('/{fpo_id}/match-bulk-order')
def match_bulk_order(fpo_id: str, request: BulkOrderMatchRequest):
    if not storage.validate_fpo(fpo_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'FPO {fpo_id} not found.')
    try:
        result = storage.match_bulk_order(fpo_id, request.buyer_order_id, request.crop, request.required_quantity_kg)
        return {'message': 'Bulk order matching completed.', **result}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
