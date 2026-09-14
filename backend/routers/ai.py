from fastapi import APIRouter, HTTPException, Depends

from pydantic import BaseModel

from backend.services.ai_client import (
    AIServiceError,
    PricePredictionRequest,
    PricePredictionResponse,
    BuyerMatchingRequest,
    BuyerMatchingResponse,
    predict_price,
    match_buyers,
)

from backend.database import get_connection
from backend.auth_dependency import get_current_user


# ==================================================
# EXISTING FRONTEND AI ROUTER
# ==================================================

router = APIRouter(
    prefix="/api/ai",
    tags=["ai"]
)


# --------------------------------------------------
# PRICE PREDICTION
# --------------------------------------------------

@router.post(
    "/predict-price",
    response_model=PricePredictionResponse
)
def predict_price_for_frontend(
    request: PricePredictionRequest
):
    try:
        return predict_price(request)

    except AIServiceError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        ) from error


# --------------------------------------------------
# BUYER MATCHING
# --------------------------------------------------

@router.post(
    "/match-buyers",
    response_model=BuyerMatchingResponse
)
def match_buyers_for_frontend(
    request: BuyerMatchingRequest
):
    try:
        return match_buyers(request)

    except AIServiceError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        ) from error


# ==================================================
# PRODUCE VOICE/TEXT PARSING
# ==================================================

produce_router = APIRouter(
    prefix="/ai",
    tags=["ai"]
)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class ProduceParseRequest(BaseModel):
    farmer_id: int
    text: str


# --------------------------------------------------
# SIMPLE PRODUCE PARSER
# --------------------------------------------------

def parse_produce_text(text: str):

    import re

    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    original_text = text.strip()

    normalized = original_text.lower().replace(",", " ")


    # ------------------------------
    # CROP
    # ------------------------------

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


    # ------------------------------
    # QUANTITY + UNIT
    # ------------------------------

    quantity = None
    unit = ""

    quantity_match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(kg|kgs|kilogram|kilograms|quintal|quintals|qtl|"
        r"ton|tons|tonne|tonnes)",
        normalized
    )

    if quantity_match:

        quantity = float(
            quantity_match.group(1)
        )

        unit_value = quantity_match.group(2)


        if unit_value in [
            "kgs",
            "kilogram",
            "kilograms"
        ]:

            unit = "kg"


        elif unit_value in [
            "quintal",
            "quintals",
            "qtl"
        ]:

            unit = "quintal"


        elif unit_value in [
            "ton",
            "tons",
            "tonne",
            "tonnes"
        ]:

            unit = "ton"


        else:

            unit = unit_value


    # ------------------------------
    # QUALITY
    # ------------------------------

    quality = ""

    quality_match = re.search(
        r"quality\s*[:\-]?\s*([a-zA-Z0-9]+)",
        original_text,
        re.IGNORECASE
    )

    if quality_match:

        quality = quality_match.group(1)


    # ------------------------------
    # EXPECTED PRICE
    # ------------------------------

    expected_price = None

    price_match = re.search(
        r"(?:expected\s*price|price)"
        r"\s*[:\-]?\s*(?:rs\.?|₹)?\s*"
        r"(\d+(?:\.\d+)?)",
        original_text,
        re.IGNORECASE
    )

    if not price_match:

        price_match = re.search(
            r"(?:rs\.?|₹)\s*"
            r"(\d+(?:\.\d+)?)",
            original_text,
            re.IGNORECASE
        )

    if price_match:

        expected_price = float(
            price_match.group(1)
        )


    # ------------------------------
    # LOCATION
    # ------------------------------

    location = ""

    location_match = re.search(
        r"(?:from|location)"
        r"\s*[:\-]?\s*([A-Za-z][A-Za-z\s]*)",
        original_text,
        re.IGNORECASE
    )

    if location_match:

        location = location_match.group(1).strip()

        location = re.sub(
            r"\s+(quality|expected|price|for|available).*",
            "",
            location,
            flags=re.IGNORECASE
        ).strip()


    # ------------------------------
    # VALIDATION
    # ------------------------------

    missing_fields = []


    if not crop_name:

        missing_fields.append(
            "crop_name"
        )


    if quantity is None or quantity <= 0:

        missing_fields.append(
            "quantity"
        )


    if not unit:

        missing_fields.append(
            "unit"
        )


    if expected_price is None or expected_price <= 0:

        missing_fields.append(
            "expected_price"
        )


    # Location is optional.
    # Therefore it is NOT added to missing_fields.


    return {

        "crop_name": crop_name,

        "quantity": quantity,

        "unit": unit,

        "quality": quality,

        "expected_price": expected_price,

        "location": (
            location
            if location
            else None
        ),

        "available_date": None,

        "missing_fields": missing_fields
    }


# --------------------------------------------------
# PARSE PRODUCE
# --------------------------------------------------

@produce_router.post(
    "/parse-produce"
)
def parse_produce(
    data: ProduceParseRequest,
    current_user=Depends(get_current_user)
):

    # ------------------------------
    # CHECK LOGGED-IN FARMER
    # ------------------------------

    token_farmer_id = current_user["user_id"]

    if data.farmer_id != token_farmer_id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You can only submit produce "
                "for your own farmer account"
            )
        )


    # ------------------------------
    # CHECK FARMER EXISTS
    # ------------------------------

    connection = get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT id, role
            FROM users
            WHERE id = %s
            """,
            (data.farmer_id,)
        )

        farmer = cursor.fetchone()

    finally:

        cursor.close()
        connection.close()


    if not farmer:

        raise HTTPException(
            status_code=404,
            detail="Farmer not found"
        )


    # ------------------------------
    # CHECK ROLE
    # ------------------------------

    if farmer["role"] != "FARMER":

        raise HTTPException(
            status_code=403,
            detail="User is not a farmer"
        )


    # ------------------------------
    # PARSE TEXT
    # ------------------------------

    try:

        result = parse_produce_text(
            data.text
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    # ------------------------------
    # RETURN RESULT
    # ------------------------------

    return {

        "farmer_id": data.farmer_id,

        **result

    }