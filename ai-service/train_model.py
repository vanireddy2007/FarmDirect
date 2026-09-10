import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
import joblib

# Load data
data = pd.read_csv("data/farmdirect_sample_mandi_prices.csv")

# Convert date
data["date"] = pd.to_datetime(data["date"])

# Sort by date
data = data.sort_values("date")

# Create features
data["lag_1_price"] = data["modal_price"].shift(1)

data["rolling_7_day_average"] = (
    data["modal_price"]
    .rolling(window=7)
    .mean()
)

# Tomorrow's price = target
data["target_price"] = data["modal_price"].shift(-1)

# Remove rows with missing values
model_data = data.dropna(
    subset=[
        "lag_1_price",
        "rolling_7_day_average",
        "target_price"
    ]
)

# Features
features = [
    "lag_1_price",
    "rolling_7_day_average"
]

X = model_data[features]
y = model_data["target_price"]

# Split data chronologically
split_index = int(len(model_data) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# Create model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

# Train model
model.fit(X_train, y_train)

# Predict test data
predictions = model.predict(X_test)

# Calculate evaluation metrics
mae = mean_absolute_error(y_test, predictions)

rmse = np.sqrt(
    mean_squared_error(y_test, predictions)
)

print("Model trained successfully!")

print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))

print("\nActual prices:")
print(y_test.values)

print("\nPredicted prices:")
print(predictions)

print("\nMODEL EVALUATION:")
print("MAE:", mae)
print("RMSE:", rmse)

joblib.dump(model, "models/price_model.joblib")

print("\nModel saved successfully!")