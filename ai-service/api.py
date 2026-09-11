from fastapi import FastAPI
from pydantic import BaseModel

from predictor import predict_price
from price_intelligence import (
    calculate_price_intelligence,
    calculate_confidence,
    generate_explanation,
    recommend_selling_window
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="FarmDirect AI Service",
    description="AI service for market price intelligence",
    version="1.0"
)


# ============================================================
# PRICE PREDICTION REQUEST MODEL
# ============================================================

class PricePredictionRequest(BaseModel):
    lag_1_price: float
    rolling_7_day_average: float
    month: int
    day_of_week: int
    current_price: float


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "FarmDirect AI Service is running!"
    }


# ============================================================
# PRICE PREDICTION
# ============================================================

@app.post("/predict-price")
def predict_market_price(
    data: PricePredictionRequest
):

    predicted_price = predict_price(
        data.lag_1_price,
        data.rolling_7_day_average,
        data.month,
        data.day_of_week
    )

    # Initial development-dataset MAE.
    # This value must be recalculated when real mandi
    # data is used for final model training.
    mae = 118.27

    price_result = calculate_price_intelligence(
        predicted_price,
        mae
    )

    confidence = calculate_confidence(
        predicted_price,
        mae
    )

    explanation = generate_explanation(
        predicted_price,
        mae
    )

    selling_window = recommend_selling_window(
        data.current_price,
        predicted_price
    )

    return {
        "predicted_price": predicted_price,
        "expected_min_price": price_result["expected_min_price"],
        "expected_max_price": price_result["expected_max_price"],
        "suggested_minimum_price": price_result["suggested_minimum_price"],
        "confidence": confidence,
        "explanation": explanation,
        "selling_window": selling_window,
        "disclaimer": (
            "This is an estimated recommendation based on "
            "available historical and market data. "
            "It is not a guaranteed future price."
        )
    }
