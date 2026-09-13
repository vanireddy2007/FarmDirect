from fastapi import FastAPI
from pydantic import BaseModel

from feature_calculator import get_market_features
from predictor import predict_price
from price_intelligence import (
    calculate_price_intelligence,
    calculate_confidence,
    generate_explanation,
    recommend_selling_window
)


app = FastAPI(
    title="FarmDirect AI Service",
    description="AI service for market price intelligence",
    version="1.0"
)


class PricePredictionRequest(BaseModel):
    commodity: str
    market: str
    current_price: float


@app.get("/")
def home():
    return {
        "message": "FarmDirect AI Service is running!"
    }


@app.post("/predict-price")
def predict_market_price(data: PricePredictionRequest):

    # Step 1: Calculate features automatically
    features = get_market_features(
        commodity=data.commodity,
        market=data.market,
        current_price=data.current_price
    )

    # Step 2: Get ML prediction
    predicted_price = predict_price(
        commodity=features["commodity"],
        market=features["market"],
        current_price=features["current_price"],
        lag_1_price=features["lag_1_price"],
        rolling_7_day_average=features["rolling_7_day_average"],
        month=features["month"],
        day_of_week=features["day_of_week"]
    )

    # Step 3: Generate price intelligence
    price_result = calculate_price_intelligence(
        predicted_price
    )

    # Step 4: Calculate confidence
    confidence = calculate_confidence(
        predicted_price
    )

    # Step 5: Generate explanation
    explanation = generate_explanation(
        predicted_price
    )

    # Step 6: Recommend selling window
    selling_window = recommend_selling_window(
        data.current_price,
        predicted_price
    )

    return {
        "commodity": data.commodity,
        "market": data.market,
        "current_price": data.current_price,

        "predicted_price": predicted_price,

        "expected_min_price":
            price_result["expected_min_price"],

        "expected_max_price":
            price_result["expected_max_price"],

        "suggested_minimum_price":
            price_result["suggested_minimum_price"],

        "confidence": confidence,

        "explanation": explanation,

        "selling_window": selling_window,

        "disclaimer": (
            "This is an estimated recommendation based on "
            "historical mandi price data and model predictions. "
            "It is not a guaranteed future price."
        )
    }