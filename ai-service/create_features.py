import pandas as pd

data = pd.read_csv("data/farmdirect_sample_mandi_prices.csv")

data["date"] = pd.to_datetime(data["date"])

data = data.sort_values("date")

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

print(data[[
    "date",
    "modal_price",
    "lag_1_price",
    "rolling_7_day_average",
    "rolling_30_day_average"
]])
# Tomorrow's modal price - our target
data["target_price"] = data["modal_price"].shift(-1)

print("\nTARGET PRICE:")
print(data[[
    "date",
    "modal_price",
    "lag_1_price",
    "rolling_7_day_average",
    "target_price"
]])

# Remove rows where target price is missing
model_data = data.dropna(subset=["target_price"])

# Select features for the model
features = [
    "lag_1_price",
    "rolling_7_day_average"
]

X = model_data[features]
y = model_data["target_price"]

print("\nMODEL INPUT (X):")
print(X.head())

print("\nTARGET (y):")
print(y.head())

print("\nTraining rows:", len(model_data))