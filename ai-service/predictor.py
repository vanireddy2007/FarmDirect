import joblib
import pandas as pd


model = joblib.load("models/price_model.joblib")


def predict_price(
    lag_1_price,
    rolling_7_day_average,
    month,
    day_of_week
):
    new_data = pd.DataFrame({
        "lag_1_price": [lag_1_price],
        "rolling_7_day_average": [rolling_7_day_average],
        "month": [month],
        "day_of_week": [day_of_week]
    })

    prediction = model.predict(new_data)

    return round(prediction[0], 2)