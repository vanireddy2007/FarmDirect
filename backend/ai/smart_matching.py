def calculate_match_score(
    crop_match,
    quantity_match,
    price_match,
    quality_match,
    location_match
):
    """
    Calculate farmer-buyer matching score.
    Each input should be between 0 and 1.
    """

    values = [
        crop_match,
        quantity_match,
        price_match,
        quality_match,
        location_match
    ]

    if any(value < 0 or value > 1 for value in values):
        raise ValueError(
            "All matching values must be between 0 and 1"
        )

    score = (
        crop_match * 0.30
        + quantity_match * 0.20
        + price_match * 0.20
        + quality_match * 0.15
        + location_match * 0.15
    )

    return round(score * 100, 2)