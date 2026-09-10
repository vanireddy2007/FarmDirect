import joblib
import pandas as pd

# Load trained model
model = joblib.load("models/price_model.joblib")


def predict_price(
    lag_1_price,
    rolling_7_day_average,
    month,
    day_of_week
):
    # Create input data for the model
    new_data = pd.DataFrame({
        "lag_1_price": [lag_1_price],
        "rolling_7_day_average": [rolling_7_day_average],
        "month": [month],
        "day_of_week": [day_of_week]
    })

    # Make prediction
    prediction = model.predict(new_data)

    return round(prediction[0], 2)


# Example farmer input
lag_1_price = 2900
rolling_7_day_average = 2780
month = 8
day_of_week = 3

# Predict tomorrow's price
predicted_price = predict_price(
    lag_1_price,
    rolling_7_day_average,
    month,
    day_of_week
)

print("PRICE PREDICTION")
print("----------------")
print("Yesterday's price: ₹", lag_1_price)
print("7-day average: ₹", rolling_7_day_average)
print("Month:", month)
print("Day of week:", day_of_week)
print("Expected market price: ₹", predicted_price)
print("Expected market price per quintal: ₹", predicted_price)