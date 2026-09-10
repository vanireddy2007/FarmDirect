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

# -----------------------------
# CREATE FEATURES
# -----------------------------

# Yesterday's modal price
data["lag_1_price"] = data["modal_price"].shift(1)

# 7-day rolling average
data["rolling_7_day_average"] = (
    data["modal_price"]
    .rolling(window=7)
    .mean()
)

# Month
data["month"] = data["date"].dt.month

# Day of week
data["day_of_week"] = data["date"].dt.dayofweek

# Tomorrow's price = target
data["target_price"] = data["modal_price"].shift(-1)

# -----------------------------
# REMOVE MISSING VALUES
# -----------------------------

model_data = data.dropna(
    subset=[
        "lag_1_price",
        "rolling_7_day_average",
        "month",
        "day_of_week",
        "target_price"
    ]
)

# -----------------------------
# SELECT FEATURES
# -----------------------------

features = [
    "lag_1_price",
    "rolling_7_day_average",
    "month",
    "day_of_week"
]

X = model_data[features]
y = model_data["target_price"]

# -----------------------------
# SPLIT DATA CHRONOLOGICALLY
# -----------------------------

split_index = int(len(model_data) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# -----------------------------
# CREATE MODEL
# -----------------------------

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

# Train model
model.fit(X_train, y_train)

# -----------------------------
# MAKE PREDICTIONS
# -----------------------------

predictions = model.predict(X_test)

# -----------------------------
# EVALUATE MODEL
# -----------------------------

mae = mean_absolute_error(y_test, predictions)

rmse = np.sqrt(
    mean_squared_error(y_test, predictions)
)

print("MODEL TRAINED SUCCESSFULLY!")
print("---------------------------")

print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))
print("Number of features:", len(features))

print("\nFeatures used:")
print(features)

print("\nActual prices:")
print(y_test.values)

print("\nPredicted prices:")
print(predictions)

print("\nMODEL EVALUATION:")
print("MAE:", round(mae, 2))
print("RMSE:", round(rmse, 2))

# -----------------------------
# SAVE MODEL
# -----------------------------

joblib.dump(model, "models/price_model.joblib")

print("\nModel saved successfully!")