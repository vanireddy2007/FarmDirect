import joblib
import pandas as pd


# Load the trained AI model
model = joblib.load("models/price_model.joblib")


def predict_price(lag_1_price, rolling_7_day_average):
    """
    Predict the next market price using the trained model.
    """

    new_data = pd.DataFrame({
        "lag_1_price": [lag_1_price],
        "rolling_7_day_average": [rolling_7_day_average]
    })

    prediction = model.predict(new_data)

    return round(prediction[0], 2)


# Test prediction
lag_1_price = 2900
rolling_7_day_average = 2780

predicted_price = predict_price(
    lag_1_price,
    rolling_7_day_average
)


print("PRICE PREDICTION")
print("----------------")

print("Yesterday's price: ₹", lag_1_price)
print("7-day average: ₹", rolling_7_day_average)
print("Expected market price: ₹", predicted_price)
print("Expected market price per quintal: ₹", predicted_price)