import pandas as pd

data = pd.read_csv("data/farmdirect_sample_mandi_prices.csv")

data["date"] = pd.to_datetime(data["date"])
data = data.sort_values("date")

# Previous day's price
data["lag_1_price"] = data["modal_price"].shift(1)

# 7-day average price
data["rolling_7_day_average"] = data["modal_price"].rolling(window=7).mean()

# 30-day average price
data["rolling_30_day_average"] = data["modal_price"].rolling(window=30).mean()

# Date-related features
data["month"] = data["date"].dt.month
data["day_of_week"] = data["date"].dt.dayofweek

# Tomorrow's price becomes our prediction target
data["target_price"] = data["modal_price"].shift(-1)

# Remove rows where the target is missing
model_data = data.dropna(subset=["target_price"])

features = [
    "lag_1_price",
    "rolling_7_day_average",
    "month",
    "day_of_week"
]

X = model_data[features]
y = model_data["target_price"]

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

print("Training rows:", len(model_data))
print("Number of features:", len(features))