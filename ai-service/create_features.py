import pandas as pd

# Load dataset
data = pd.read_csv("data/farmdirect_sample_mandi_prices.csv")

# Convert date column
data["date"] = pd.to_datetime(data["date"])

# Sort by date
data = data.sort_values("date")

# -----------------------------
# PRICE FEATURES
# -----------------------------

# Yesterday's modal price
data["lag_1_price"] = data["modal_price"].shift(1)

# 7-day rolling average
data["rolling_7_day_average"] = (
    data["modal_price"]
    .rolling(window=7)
    .mean()
)

# 30-day rolling average
data["rolling_30_day_average"] = (
    data["modal_price"]
    .rolling(window=30)
    .mean()
)

# -----------------------------
# TIME FEATURES
# -----------------------------

# Month of the year
data["month"] = data["date"].dt.month

# Day of the week
data["day_of_week"] = data["date"].dt.dayofweek

# -----------------------------
# TARGET
# -----------------------------

# Tomorrow's modal price
data["target_price"] = data["modal_price"].shift(-1)

# Remove rows where target is missing
model_data = data.dropna(subset=["target_price"])

# -----------------------------
# MODEL FEATURES
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
# DISPLAY RESULTS
# -----------------------------

print("\nFEATURE DATA:")
print(data[[
    "date",
    "modal_price",
    "lag_1_price",
    "rolling_7_day_average",
    "rolling_30_day_average",
    "month",
    "day_of_week"
]].tail(10))

print("\nMODEL INPUT (X):")
print(X.head())

print("\nTARGET (y):")
print(y.head())

print("\nTraining rows:", len(model_data))
print("Number of features:", len(features))