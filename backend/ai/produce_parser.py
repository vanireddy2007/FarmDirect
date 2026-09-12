import re


def parse_produce_text(text: str):
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    original_text = text.strip()

    # Normalize common separators
    normalized = original_text.lower().replace(",", " ")

    # -----------------------------
    # CROP
    # -----------------------------
    crop_name = ""

    known_crops = [
        "paddy",
        "rice",
        "wheat",
        "maize",
        "corn",
        "cotton",
        "tomato",
        "potato",
        "onion",
        "chilli",
        "chili",
        "turmeric",
        "groundnut",
        "soybean",
        "sugarcane"
    ]

    for crop in known_crops:
        if crop in normalized:
            crop_name = crop
            break

    # -----------------------------
    # QUANTITY + UNIT
    # -----------------------------
    quantity = None
    unit = ""

    quantity_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(kg|kgs|kilogram|kilograms|quintal|quintals|qtl|ton|tons|tonne|tonnes)",
        normalized
    )

    if quantity_match:
        quantity = float(quantity_match.group(1))
        unit_value = quantity_match.group(2)

        if unit_value in ["kgs", "kilogram", "kilograms"]:
            unit = "kg"
        elif unit_value in ["quintal", "quintals", "qtl"]:
            unit = "quintal"
        elif unit_value in ["ton", "tons", "tonne", "tonnes"]:
            unit = "ton"
        else:
            unit = unit_value

    # -----------------------------
    # QUALITY
    # -----------------------------
    quality = ""

    quality_match = re.search(
        r"quality\s*[:\-]?\s*([a-zA-Z0-9]+)",
        original_text,
        re.IGNORECASE
    )

    if quality_match:
        quality = quality_match.group(1)

    # -----------------------------
    # EXPECTED PRICE
    # -----------------------------
    expected_price = None

    price_match = re.search(
        r"(?:expected\s*price|price)\s*[:\-]?\s*(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)",
        original_text,
        re.IGNORECASE
    )

    if not price_match:
        price_match = re.search(
            r"(?:rs\.?|₹)\s*(\d+(?:\.\d+)?)",
            original_text,
            re.IGNORECASE
        )

    if price_match:
        expected_price = float(price_match.group(1))

    # -----------------------------
    # LOCATION
    # -----------------------------
    location = ""

    location_match = re.search(
        r"(?:from|location)\s*[:\-]?\s*([A-Za-z][A-Za-z\s]*)",
        original_text,
        re.IGNORECASE
    )

    if location_match:
        location = location_match.group(1).strip()

        # Remove trailing common phrases
        location = re.sub(
            r"\s+(quality|expected|price|for|available).*",
            "",
            location,
            flags=re.IGNORECASE
        ).strip()

    # -----------------------------
    # MISSING FIELDS
    # -----------------------------
    missing_fields = []

    if not crop_name:
        missing_fields.append("crop_name")

    if quantity is None or quantity <= 0:
        missing_fields.append("quantity")

    if not unit:
        missing_fields.append("unit")

    if expected_price is None or expected_price <= 0:
        missing_fields.append("expected_price")

    if not location:
        missing_fields.append("location")

    return {
        "crop_name": crop_name,
        "quantity": quantity,
        "unit": unit,
        "quality": quality,
        "expected_price": expected_price,
        "location": location if location else None,
        "available_date": None,
        "missing_fields": missing_fields
    }