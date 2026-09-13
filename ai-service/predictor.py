import joblib
import pandas as pd


# Load the corrected trained model
model = joblib.load("models/corrected_price_model.joblib")


def predict_price(
    commodity,
    market,
    current_price,
    lag_1_price,
    rolling_7_day_average,
    month,
    day_of_week
):
    data = pd.DataFrame({
        "Commodity": [commodity],
        "Market": [market],
        "Modal Price": [current_price],
        "lag_1_price": [lag_1_price],
        "rolling_7_day_average": [rolling_7_day_average],
        "month": [month],
        "day_of_week": [day_of_week]
    })

    prediction = model.predict(data)

    return round(float(prediction[0]), 2)