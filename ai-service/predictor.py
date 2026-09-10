import joblib
import pandas as pd

# Load the trained AI model
model = joblib.load("models/price_model.joblib")

# Example new market information
new_data = pd.DataFrame({
    "lag_1_price": [2900],
    "rolling_7_day_average": [2780]
})

# Make prediction
prediction = model.predict(new_data)

print("Expected market price:", prediction[0])
print("Expected market price per quintal: ₹", round(prediction[0], 2))
