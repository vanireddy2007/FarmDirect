from fastapi import FastAPI
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


@app.get("/")
def home():
    return {
        "message": "FarmDirect AI Service is running!"
    }


@app.post("/predict-price")
def predict_market_price(
    lag_1_price: float,
    rolling_7_day_average: float,
    month: int,
    day_of_week: int,
    current_price: float
):
    # Predict price
    predicted_price = predict_price(
        lag_1_price,
        rolling_7_day_average,
        month,
        day_of_week
    )

    # Current prototype MAE
    mae = 118.27

    # Calculate price intelligence
    price_result = calculate_price_intelligence(
        predicted_price,
        mae
    )

    # Calculate confidence
    confidence = calculate_confidence(
        predicted_price,
        mae
    )

    # Generate explanation
    explanation = generate_explanation(
        predicted_price,
        mae
    )

    # Recommend selling window
    selling_window = recommend_selling_window(
        current_price,
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