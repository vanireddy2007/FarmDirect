MODEL_MAE = 156.15


def calculate_price_intelligence(predicted_price):
    """
    Creates an estimated price range around the model prediction.

    The range is a prototype estimate based on the model's
    historical MAE. It is NOT a statistically calibrated
    prediction interval.
    """

    expected_min_price = max(0, predicted_price - MODEL_MAE)
    expected_max_price = predicted_price + MODEL_MAE

    # Conservative suggested minimum.
    suggested_minimum = predicted_price - (MODEL_MAE * 0.5)
    suggested_minimum = max(0, suggested_minimum)

    return {
        "expected_min_price": round(expected_min_price, 2),
        "expected_max_price": round(expected_max_price, 2),
        "suggested_minimum_price": round(suggested_minimum, 2)
    }


def calculate_confidence(predicted_price):
    """
    Prototype confidence indicator based on
    historical MAE relative to predicted price.
    """

    error_percentage = (MODEL_MAE / predicted_price) * 100

    if error_percentage <= 5:
        return "High"
    elif error_percentage <= 10:
        return "Medium"
    else:
        return "Low"


def generate_explanation(predicted_price):
    error_percentage = (MODEL_MAE / predicted_price) * 100

    if error_percentage <= 5:
        reliability = "historical price patterns are relatively consistent"
    elif error_percentage <= 10:
        reliability = "there is moderate variation in historical price patterns"
    else:
        reliability = "historical price variation is relatively high"

    return (
        f"The expected price is based on historical mandi price patterns. "
        f"The model's historical average prediction error is approximately "
        f"₹{MODEL_MAE:.2f} per quintal ({error_percentage:.1f}%), "
        f"indicating that {reliability}."
    )


def recommend_selling_window(current_price, predicted_price):

    difference_percentage = (
        (predicted_price - current_price) / current_price
    ) * 100

    if difference_percentage >= 5:
        return (
            "The expected price is higher than the current price. "
            "Consider waiting if storage and market conditions allow."
        )

    elif difference_percentage <= -5:
        return (
            "The expected price is lower than the current price. "
            "Consider selling now if the current offer is acceptable."
        )

    else:
        return (
            "The current price is close to the expected price. "
            "Selling now may be reasonable if the offer is acceptable."
        )