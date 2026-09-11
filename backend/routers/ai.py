from fastapi import APIRouter, HTTPException

from services.ai_client import (
    AIServiceError,
    PricePredictionRequest,
    PricePredictionResponse,
    BuyerMatchingRequest,
    BuyerMatchingResponse,
    predict_price,
    match_buyers,
)


router = APIRouter(prefix="/api/ai", tags=["ai"])


# --------------------------------------------------
# PRICE PREDICTION
# --------------------------------------------------

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


# --------------------------------------------------
# BUYER MATCHING
# --------------------------------------------------

@router.post(
    "/match-buyers",
    response_model=BuyerMatchingResponse
)
def match_buyers_for_frontend(
    request: BuyerMatchingRequest
):
    try:
        return match_buyers(request)

    except AIServiceError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        ) from error