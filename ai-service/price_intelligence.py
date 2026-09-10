# Price Intelligence for FarmDirect

from predictor import predict_price


def calculate_price_intelligence(predicted_price, mae):
    """
    Creates an estimated price range using
    the model's Mean Absolute Error (MAE).
    """

    expected_min_price = predicted_price - mae
    expected_max_price = predicted_price + mae

    suggested_minimum = predicted_price - (mae * 0.5)

    return {
        "expected_min_price": round(expected_min_price, 2),
        "expected_max_price": round(expected_max_price, 2),
        "suggested_minimum_price": round(suggested_minimum, 2)
    }


def calculate_confidence(predicted_price, mae):
    """
    Estimates confidence based on model error.
    """

    error_percentage = (mae / predicted_price) * 100

    if error_percentage <= 5:
        return "High"
    elif error_percentage <= 10:
        return "Medium"
    else:
        return "Low"


def generate_explanation(predicted_price, mae):
    """
    Generates a simple explanation for the farmer.
    """

    error_percentage = (mae / predicted_price) * 100

    if error_percentage <= 5:
        reliability = "recent price trends are relatively consistent"
    elif error_percentage <= 10:
        reliability = "there is some variation in recent price trends"
    else:
        reliability = "price variation is relatively high"

    return (
        f"The expected price is based on recent market-price patterns. "
        f"The model's average prediction error is about "
        f"{error_percentage:.1f}%, indicating that {reliability}."
    )


def recommend_selling_window(current_price, predicted_price):
    """
    Gives a simple selling-window recommendation.
    """

    difference_percentage = (
        (predicted_price - current_price) / current_price
    ) * 100

    if difference_percentage >= 5:
        return "Consider waiting if storage and market conditions allow."

    elif difference_percentage <= -5:
        return "Consider selling now if the current offer is acceptable."

    else:
        return "Current price is close to the expected price; selling now is reasonable."


# --------------------------------
# CURRENT PROTOTYPE VALUES
# --------------------------------

predicted_price = predict_price(
    lag_1_price=2900,
    rolling_7_day_average=2780,
    month=8,
    day_of_week=3
)

# MAE from the NEW model
mae = 118.27

# Current market price
current_price = 2600


# --------------------------------
# CALCULATE PRICE INTELLIGENCE
# --------------------------------

result = calculate_price_intelligence(
    predicted_price,
    mae
)

confidence = calculate_confidence(
    predicted_price,
    mae
)

explanation = generate_explanation(
    predicted_price,
    mae
)

selling_window = recommend_selling_window(
    current_price,
    predicted_price
)


# --------------------------------
# DISPLAY RESULTS
# --------------------------------

print("PRICE INTELLIGENCE")
print("------------------")

print(
    "Expected minimum price: ₹",
    result["expected_min_price"]
)

print(
    "Expected maximum price: ₹",
    result["expected_max_price"]
)

print(
    "Suggested minimum price: ₹",
    result["suggested_minimum_price"]
)

print("Confidence:", confidence)

print("Explanation:", explanation)

print("Selling window:", selling_window)

print("\nDisclaimer:")
print(
    "This is an estimated recommendation based on "
    "available historical and market data. "
    "It is not a guaranteed future price."
)