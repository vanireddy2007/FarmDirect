from fastapi import FastAPI, Depends, HTTPException
import os
import httpx
from dotenv import load_dotenv

from database import get_connection

from routers.auth import router as auth_router
from routers.produce import router as produce_router
from routers.orders import router as orders_router
from routers.offers import router as offers_router
from routers.aggregation import router as aggregation_router
from routers.ai import router as ai_router, produce_router as ai_produce_router

from auth_dependency import get_current_user

from ai.demand_prediction import predict_demand
from ai.fair_price import recommend_fair_price
from ai.smart_matching import calculate_match_score

from ai.matching_service import (
    calculate_crop_match,
    calculate_quantity_match,
    calculate_price_match,
    calculate_quality_match,
    calculate_location_match
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")
LANGUAGE_SERVICE_URL = os.getenv("LANGUAGE_SERVICE_URL")


# ============================================================
# APP
# ============================================================

app = FastAPI()


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    auth_router,
    prefix="/auth"
)

app.include_router(
    produce_router,
    prefix="/produce"
)

app.include_router(
    orders_router,
    prefix="/orders"
)

app.include_router(
    offers_router,
    prefix="/offers"
)

app.include_router(
    aggregation_router,
    prefix="/aggregation"
)

app.include_router(ai_router)

app.include_router(ai_produce_router)


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "FarmDirect Backend is running"
    }


# ============================================================
# DATABASE TEST
# ============================================================

@app.get("/test-db")
def test_database():

    connection = get_connection()

    if connection.is_connected():

        connection.close()

        return {
            "message": "MySQL connected successfully"
        }

    return {
        "message": "MySQL connection failed"
    }


# ============================================================
# PROTECTED ROUTE
# ============================================================

@app.get("/protected")
def protected_route(
    current_user=Depends(get_current_user)
):

    return {
        "message": "You are authenticated",
        "user": current_user
    }


# ============================================================
# AI DEMAND PREDICTION
# ============================================================

@app.post("/ai/demand")
def demand_prediction(
    crop_name: str,
    historical_demand: str,
    current_month: int,
    future_periods: int = 1
):

    try:

        values = [
            float(value.strip())
            for value in historical_demand.split(",")
            if value.strip()
        ]

        predictions = predict_demand(
            values,
            future_periods,
            current_month
        )

        return {
            "crop_name": crop_name,
            "current_month": current_month,
            "historical_demand": values,
            "predicted_demand": [
                round(value, 2)
                for value in predictions
            ]
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ============================================================
# AI DEMAND PREDICTION FROM ORDERS
# ============================================================

@app.get("/ai/demand/from-orders")
def demand_from_orders(
    crop_name: str
):

    connection = get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    query = """
    SELECT
        DATE(o.created_at) AS order_date,
        SUM(o.quantity) AS total_demand
    FROM orders o
    JOIN produce p
        ON o.produce_id = p.id
    WHERE LOWER(p.crop_name) = LOWER(%s)
      AND o.status IN (
          'PENDING',
          'ACCEPTED',
          'COMPLETED'
      )
    GROUP BY DATE(o.created_at)
    ORDER BY order_date
    """

    cursor.execute(
        query,
        (crop_name,)
    )

    rows = cursor.fetchall()


    # ========================================================
    # AT LEAST 2 DIFFERENT DAYS
    # ========================================================

    if len(rows) >= 2:

        historical_demand = [
            float(row["total_demand"])
            for row in rows
        ]

        current_month = (
            rows[-1]["order_date"].month
        )

        predictions = predict_demand(
            historical_demand,
            1,
            current_month
        )

        cursor.close()
        connection.close()

        return {
            "crop_name": crop_name,
            "current_month": current_month,
            "historical_demand": historical_demand,
            "predicted_demand": [
                round(value, 2)
                for value in predictions
            ],
            "data_source": "FarmDirect orders"
        }


    # ========================================================
    # FALLBACK: INDIVIDUAL ORDERS
    # ========================================================

    fallback_query = """
    SELECT
        o.quantity AS demand,
        o.created_at
    FROM orders o
    JOIN produce p
        ON o.produce_id = p.id
    WHERE LOWER(p.crop_name) = LOWER(%s)
      AND o.status IN (
          'PENDING',
          'ACCEPTED',
          'COMPLETED'
      )
    ORDER BY o.created_at
    """

    cursor.execute(
        fallback_query,
        (crop_name,)
    )

    fallback_rows = cursor.fetchall()

    cursor.close()
    connection.close()


    if len(fallback_rows) < 2:

        raise HTTPException(
            status_code=400,
            detail="At least 2 orders are required for demand prediction"
        )


    historical_demand = [
        float(row["demand"])
        for row in fallback_rows
    ]

    current_month = (
        fallback_rows[-1]["created_at"].month
    )

    predictions = predict_demand(
        historical_demand,
        1,
        current_month
    )

    return {
        "crop_name": crop_name,
        "current_month": current_month,
        "historical_demand": historical_demand,
        "predicted_demand": [
            round(value, 2)
            for value in predictions
        ],
        "data_source": "FarmDirect orders"
    }


# ============================================================
# FAIR PRICE RECOMMENDATION
# ============================================================

@app.post("/ai/fair-price")
def fair_price_prediction(
    expected_price: float,
    predicted_demand: float,
    average_market_price: float
):

    try:

        result = recommend_fair_price(
            expected_price,
            predicted_demand,
            average_market_price
        )

        return {
            "expected_price": expected_price,
            "predicted_demand": predicted_demand,
            "average_market_price": average_market_price,
            "fair_price": result["recommended_price"],
            "price_range": result["price_range"],
            "demand_factor": result["demand_factor"]
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ============================================================
# SMART MATCH SCORE
# ============================================================

@app.post("/ai/smart-match")
def smart_match(
    crop_match: float,
    quantity_match: float,
    price_match: float,
    quality_match: float,
    location_match: float
):

    try:

        score = calculate_match_score(
            crop_match,
            quantity_match,
            price_match,
            quality_match,
            location_match
        )

        return {
            "match_score": score,
            "rating": (
                "Excellent"
                if score >= 80
                else "Good"
                if score >= 60
                else "Average"
                if score >= 40
                else "Low"
            )
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ============================================================
# REAL FARMER-BUYER MATCHING
# ============================================================

@app.post("/ai/real-match")
def real_match(
    buyer_crop: str,
    required_quantity: float,
    buyer_price: float,
    buyer_quality: str = "",
    buyer_location: str = ""
):

    if required_quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Required quantity must be greater than 0"
        )

    if buyer_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Buyer price must be greater than 0"
        )

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
        SELECT
            id,
            farmer_id,
            crop_name,
            quantity,
            unit,
            quality,
            expected_price,
            location,
            available_date,
            created_at
        FROM produce
        WHERE quantity > 0
        ORDER BY created_at DESC
        """

        cursor.execute(query)
        farmers = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    matches = []

    for farmer in farmers:

        crop_match = calculate_crop_match(
            farmer["crop_name"],
            buyer_crop
        )

        quantity_match = calculate_quantity_match(
            float(farmer["quantity"]),
            required_quantity
        )

        price_match = calculate_price_match(
            float(farmer["expected_price"]),
            buyer_price
        )

        quality_match = calculate_quality_match(
            farmer["quality"] or "",
            buyer_quality
        )

        location_match = calculate_location_match(
            farmer["location"] or "",
            buyer_location
        )

        score = calculate_match_score(
            crop_match,
            quantity_match,
            price_match,
            quality_match,
            location_match
        )

        matches.append({
            "produce_id": farmer["id"],
            "farmer_id": farmer["farmer_id"],
            "crop_name": farmer["crop_name"],
            "available_quantity": float(farmer["quantity"]),
            "unit": farmer["unit"],
            "quality": farmer["quality"],
            "expected_price": float(farmer["expected_price"]),
            "location": farmer["location"],
            "match_score": score
        })

    matches.sort(
        key=lambda item: item["match_score"],
        reverse=True
    )

    return {
        "buyer_crop": buyer_crop,
        "required_quantity": required_quantity,
        "buyer_price": buyer_price,
        "matches": matches
    }

# ============================================================
# MEMBER 4 AI PRICE PREDICTION SERVICE
# ============================================================

@app.post("/ai/member4/predict-price")
async def member4_predict_price(data: dict):

    if not AI_SERVICE_URL:
        raise HTTPException(
            status_code=500,
            detail="AI_SERVICE_URL is not configured"
        )

    required_fields = [
        "lag_1_price",
        "rolling_7_day_average",
        "month",
        "day_of_week",
        "current_price"
    ]

    for field in required_fields:

        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {field}"
            )

    payload = {
        "lag_1_price": data["lag_1_price"],
        "rolling_7_day_average": data["rolling_7_day_average"],
        "month": data["month"],
        "day_of_week": data["day_of_week"],
        "current_price": data["current_price"]
    }

    try:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                f"{AI_SERVICE_URL}/predict-price",
                json=payload
            )

        if response.status_code != 200:

            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except httpx.RequestError as e:

        raise HTTPException(
            status_code=503,
            detail=f"AI service unavailable: {str(e)}"
        )
# ============================================================
# LANGUAGE SERVICE - TRANSLATION
# ============================================================

@app.post("/language/translate")
async def language_translate(data: dict):

    if not LANGUAGE_SERVICE_URL:
        raise HTTPException(
            status_code=500,
            detail="LANGUAGE_SERVICE_URL is not configured"
        )

    required_fields = [
        "text",
        "source_language",
        "target_language"
    ]

    for field in required_fields:

        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {field}"
            )

    payload = {
        "text": data["text"],
        "source_language": data["source_language"],
        "target_language": data["target_language"]
    }

    try:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                f"{LANGUAGE_SERVICE_URL}/translate",
                json=payload
            )

        if response.status_code != 200:

            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except httpx.RequestError as e:

        raise HTTPException(
            status_code=503,
            detail=f"Language service unavailable: {str(e)}"
        )
        
