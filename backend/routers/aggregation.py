from fastapi import APIRouter, HTTPException, Depends
from database import get_connection
from role_dependency import require_role

router = APIRouter()


@router.post("/create")
def create_aggregation(
    current_user=Depends(require_role("FPO")),
    crop_name: str = "",
    required_quantity: float = 0,
    unit: str = "",
    location: str = ""
):
    if required_quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Required quantity must be greater than 0"
        )

    fpo_id = current_user["user_id"]

    connection = get_connection()
    cursor = connection.cursor()

    query = """
    INSERT INTO aggregations
    (fpo_id, crop_name, total_quantity, unit, location, required_quantity)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            fpo_id,
            crop_name,
            0,
            unit,
            location,
            required_quantity
        )
    )

    connection.commit()

    aggregation_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return {
        "message": "Aggregation created successfully",
        "aggregation_id": aggregation_id,
        "fpo_id": fpo_id
    }


@router.get("/all")
def get_all_aggregations():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        id,
        fpo_id,
        crop_name,
        total_quantity,
        unit,
        location,
        required_quantity,
        status,
        created_at
    FROM aggregations
    ORDER BY created_at DESC
    """

    cursor.execute(query)
    aggregations = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "aggregations": aggregations
    }


@router.post("/add-produce")
def add_produce_to_aggregation(
    current_user=Depends(require_role("FARMER")),
    aggregation_id: int = 0,
    produce_id: int = 0,
    quantity: float = 0
):
    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        id,
        crop_name,
        total_quantity,
        required_quantity,
        status
    FROM aggregations
    WHERE id = %s
    """

    cursor.execute(
        query,
        (aggregation_id,)
    )

    aggregation = cursor.fetchone()

    if aggregation is None:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Aggregation not found"
        )

    if aggregation["status"] != "OPEN":
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Aggregation is not open"
        )

    query = """
    SELECT
        id,
        farmer_id,
        crop_name,
        quantity,
        unit
    FROM produce
    WHERE id = %s
    """

    cursor.execute(
        query,
        (produce_id,)
    )

    produce = cursor.fetchone()

    if produce is None:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Produce not found"
        )

    if produce["farmer_id"] != current_user["user_id"]:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=403,
            detail="You can only add your own produce"
        )

    if produce["crop_name"].lower() != aggregation["crop_name"].lower():
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Crop does not match aggregation"
        )

    if quantity > float(produce["quantity"]):
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Not enough produce available"
        )

    remaining_quantity = (
        float(aggregation["required_quantity"])
        - float(aggregation["total_quantity"])
    )

    if quantity > remaining_quantity:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Quantity exceeds aggregation requirement"
        )

    insert_query = """
    INSERT INTO aggregation_items
    (aggregation_id, produce_id, farmer_id, quantity)
    VALUES (%s, %s, %s, %s)
    """

    cursor.execute(
        insert_query,
        (
            aggregation_id,
            produce_id,
            current_user["user_id"],
            quantity
        )
    )

    update_produce = """
    UPDATE produce
    SET quantity = quantity - %s
    WHERE id = %s
    """

    cursor.execute(
        update_produce,
        (
            quantity,
            produce_id
        )
    )

    new_total = (
        float(aggregation["total_quantity"])
        + quantity
    )

    if new_total >= float(aggregation["required_quantity"]):
        new_status = "COMPLETED"
    else:
        new_status = "OPEN"

    update_aggregation = """
    UPDATE aggregations
    SET total_quantity = %s,
        status = %s
    WHERE id = %s
    """

    cursor.execute(
        update_aggregation,
        (
            new_total,
            new_status,
            aggregation_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Produce added to aggregation successfully",
        "aggregation_id": aggregation_id,
        "produce_id": produce_id,
        "quantity_added": quantity,
        "total_quantity": new_total,
        "status": new_status
    }


@router.get("/{aggregation_id}/contributors")
def get_aggregation_contributors(
    aggregation_id: int
):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        ai.id,
        ai.aggregation_id,
        ai.produce_id,
        ai.farmer_id,
        u.name AS farmer_name,
        ai.quantity,
        p.crop_name,
        p.unit,
        ai.created_at
    FROM aggregation_items ai
    JOIN users u
        ON ai.farmer_id = u.id
    JOIN produce p
        ON ai.produce_id = p.id
    WHERE ai.aggregation_id = %s
    ORDER BY ai.created_at ASC
    """

    cursor.execute(
        query,
        (aggregation_id,)
    )

    contributors = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "aggregation_id": aggregation_id,
        "contributors": contributors
    }