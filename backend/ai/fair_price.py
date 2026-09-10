def recommend_fair_price(
    expected_price,
    predicted_demand,
    average_market_price
):
    if expected_price <= 0:
        raise ValueError("Expected price must be greater than 0")

    if predicted_demand < 0:
        raise ValueError("Predicted demand cannot be negative")

    if average_market_price <= 0:
        raise ValueError(
            "Average market price must be greater than 0"
        )

    # Compare predicted demand with a simple reference level
    demand_ratio = predicted_demand / 1000

    # Demand adjustment
    if demand_ratio >= 1.2:
        demand_factor = 1.10
    elif demand_ratio >= 0.8:
        demand_factor = 1.05
    elif demand_ratio >= 0.5:
        demand_factor = 1.00
    else:
        demand_factor = 0.95

    # Combine farmer expectation and market price
    base_price = (
        expected_price * 0.4
        + average_market_price * 0.6
    )

    recommended_price = base_price * demand_factor

    lower_price = recommended_price * 0.95
    upper_price = recommended_price * 1.05

    return {
        "recommended_price": round(recommended_price, 2),
        "price_range": {
            "minimum": round(lower_price, 2),
            "maximum": round(upper_price, 2)
        },
        "demand_factor": demand_factor
    }