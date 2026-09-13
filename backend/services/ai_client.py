import httpx

from pydantic import BaseModel, ConfigDict, Field

from backend.config import AI_SERVICE_TIMEOUT_SECONDS, AI_SERVICE_URL

# --------------------------------------------------
# PRICE PREDICTION
# --------------------------------------------------

class PricePredictionRequest(BaseModel):
    commodity: str
    market: str
    current_price: float = Field(gt=0)
    lag_1_price: float = Field(gt=0)
    rolling_7_day_average: float = Field(gt=0)
    month: int = Field(ge=1, le=12)
    day_of_week: int = Field(ge=0, le=6)


class PricePredictionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    predicted_price: float
    expected_min_price: float
    expected_max_price: float
    suggested_minimum_price: float
    confidence: str
    explanation: str
    selling_window: str
    disclaimer: str


class AIServiceError(Exception):
    """Raised when the separate AI service cannot provide a valid prediction."""


def predict_price(
    request: PricePredictionRequest
) -> PricePredictionResponse:
    try:
        with httpx.Client(timeout=AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/predict-price",
                json=request.model_dump()
            )

            response.raise_for_status()

            return PricePredictionResponse.model_validate(
                response.json()
            )

    except (httpx.TimeoutException, httpx.RequestError) as error:
        raise AIServiceError(
            "AI price prediction service is unavailable"
        ) from error

    except (httpx.HTTPStatusError, ValueError) as error:
        raise AIServiceError(
            "AI price prediction service returned an invalid response"
        ) from error

# --------------------------------------------------
# BUYER MATCHING
# --------------------------------------------------

class Buyer(BaseModel):
    name: str
    crop: str
    quantity: float
    quality: str
    distance: float
    verified: bool


class Farmer(BaseModel):
    crop: str
    quantity: float
    quality: str
    location: str


class BuyerMatchingRequest(BaseModel):
    farmer: Farmer
    buyers: list[Buyer]


class BuyerMatchingResponse(BaseModel):
    farmer: Farmer
    matched_buyers: list[dict]


def match_buyers(
    request: BuyerMatchingRequest
) -> BuyerMatchingResponse:
    try:
        with httpx.Client(timeout=AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{AI_SERVICE_URL.replace(':8001', ':8002')}/match-buyers",
                json=request.model_dump()
            )

            response.raise_for_status()

            return BuyerMatchingResponse.model_validate(
                response.json()
            )

    except (httpx.TimeoutException, httpx.RequestError) as error:
        raise AIServiceError(
            "AI buyer matching service is unavailable"
        ) from error

    except (httpx.HTTPStatusError, ValueError) as error:
        raise AIServiceError(
            "AI buyer matching service returned an invalid response"
        ) from error