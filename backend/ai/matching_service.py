def calculate_crop_match(farmer_crop, buyer_crop):
    if farmer_crop.lower() == buyer_crop.lower():
        return 1.0

    return 0.0


def calculate_quantity_match(
    available_quantity,
    required_quantity
):
    if required_quantity <= 0:
        return 0.0

    if available_quantity >= required_quantity:
        return 1.0

    return round(
        available_quantity / required_quantity,
        2
    )


def calculate_price_match(
    farmer_price,
    buyer_price
):
    if farmer_price <= 0 or buyer_price <= 0:
        return 0.0

    difference = abs(
        farmer_price - buyer_price
    )

    ratio = difference / buyer_price

    return round(
        max(0, 1 - ratio),
        2
    )


def calculate_quality_match(
    farmer_quality,
    buyer_quality
):
    if not buyer_quality:
        return 1.0

    if farmer_quality.lower() == buyer_quality.lower():
        return 1.0

    return 0.5


def calculate_location_match(
    farmer_location,
    buyer_location
):
    if not farmer_location or not buyer_location:
        return 0.5

    if farmer_location.lower() == buyer_location.lower():
        return 1.0

    return 0.5