from fastapi import APIRouter, Depends
from database import get_connection
from role_dependency import require_role

router = APIRouter()


@router.post("/add")
def add_produce(
    current_user=Depends(require_role("FARMER")),
    crop_name: str = "",
    quantity: float = 0,
    unit: str = "",
    quality: str = "",
    expected_price: float = 0,
    location: str = "",
    available_date: str = ""
):
    farmer_id = current_user["user_id"]

    connection = get_connection()
    cursor = connection.cursor()

    query = """
    INSERT INTO produce
    (farmer_id, crop_name, quantity, unit, quality,
     expected_price, location, available_date)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            farmer_id,
            crop_name,
            quantity,
            unit,
            quality,
            expected_price,
            location,
            available_date
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Produce added successfully",
        "farmer_id": farmer_id
    }


@router.get("/farmer/{farmer_id}")
def get_farmer_produce(farmer_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

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
    WHERE farmer_id = %s
    """

    cursor.execute(query, (farmer_id,))
    produce = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "farmer_id": farmer_id,
        "produce": produce
    }


@router.get("/all")
def get_all_produce():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

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
    ORDER BY created_at DESC
    """

    cursor.execute(query)
    produce = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "produce": produce
    }


@router.get("/search")
def search_produce(crop_name: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

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
    WHERE LOWER(crop_name) LIKE LOWER(%s)
      AND quantity > 0
    ORDER BY created_at DESC
    """

    cursor.execute(
        query,
        (f"%{crop_name}%",)
    )

    produce = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "search": crop_name,
        "produce": produce
    }