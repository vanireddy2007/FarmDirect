from fastapi import APIRouter, HTTPException

from services.ai_client import (
    AIServiceError,
    PricePredictionRequest,
    PricePredictionResponse,
    predict_price,
)


router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post(
    "/predict-price",
    response_model=PricePredictionResponse
)
def predict_price_for_frontend(
    request: PricePredictionRequest
):
    try:
        return predict_price(request)
    except AIServiceError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        ) from error