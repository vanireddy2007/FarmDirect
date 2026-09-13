from feature_calculator import get_market_features
from predictor import predict_price


print("Testing real price prediction...")
print()


# Farmer input
commodity = "Tomato"
market = "Bowenpally APMC"
current_price = 2400


# Automatically calculate model features
features = get_market_features(
    commodity=commodity,
    market=market,
    current_price=current_price
)


# Send features to ML model
predicted_price = predict_price(
    commodity=features["commodity"],
    market=features["market"],
    current_price=features["current_price"],
    lag_1_price=features["lag_1_price"],
    rolling_7_day_average=features["rolling_7_day_average"],
    month=features["month"],
    day_of_week=features["day_of_week"]
)


print("==============================")
print("REAL ML PREDICTION")
print("==============================")

print()
print("Crop:", commodity)
print("Market:", market)
print("Current price: ₹", current_price)

print()
print("Previous price: ₹", features["lag_1_price"])
print(
    "7-day average: ₹",
    features["rolling_7_day_average"]
)

print()
print("Predicted next price: ₹", predicted_price)