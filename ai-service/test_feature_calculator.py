from feature_calculator import get_market_features


print("Testing automatic feature calculation...")
print()


features = get_market_features(
    commodity="Tomato",
    market="Bowenpally APMC",
    current_price=2400
)


print("FEATURE CALCULATION SUCCESSFUL!")
print("--------------------------------")

for key, value in features.items():
    print(f"{key}: {value}")