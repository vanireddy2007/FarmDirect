from fastapi import APIRouter, HTTPException, Depends

from backend.database import get_connection

from backend.role_dependency import require_role

router = APIRouter()


@router.post("/place")
def place_offer(
    current_user=Depends(require_role("BUYER")),
    produce_id: int = 0,
    quantity: float = 0,
    offered_price: float = 0
):
    buyer_id = current_user["user_id"]

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT id, quantity
    FROM produce
    WHERE id = %s
    """

    cursor.execute(query, (produce_id,))
    produce = cursor.fetchone()

    if produce is None:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Produce not found"
        )

    if quantity <= 0 or quantity > float(produce["quantity"]):
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Invalid quantity"
        )

    if offered_price <= 0:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Invalid offered price"
        )

    insert_query = """
    INSERT INTO offers
    (buyer_id, produce_id, quantity, offered_price)
    VALUES (%s, %s, %s, %s)
    """

    cursor.execute(
        insert_query,
        (
            buyer_id,
            produce_id,
            quantity,
            offered_price
        )
    )

    connection.commit()

    offer_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return {
        "message": "Offer placed successfully",
        "offer_id": offer_id,
        "buyer_id": buyer_id
    }


@router.get("/produce/{produce_id}")
def get_produce_offers(produce_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        o.id AS offer_id,
        o.buyer_id,
        o.produce_id,
        p.crop_name,
        o.quantity,
        p.unit,
        o.offered_price,
        o.status,
        o.created_at
    FROM offers o
    JOIN produce p ON o.produce_id = p.id
    WHERE o.produce_id = %s
    ORDER BY o.created_at DESC
    """

    cursor.execute(query, (produce_id,))
    offers = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "produce_id": produce_id,
        "offers": offers
    }


@router.get("/buyer/{buyer_id}")
def get_buyer_offers(buyer_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        o.id AS offer_id,
        o.buyer_id,
        o.produce_id,
        p.crop_name,
        o.quantity,
        p.unit,
        o.offered_price,
        o.status,
        o.created_at
    FROM offers o
    JOIN produce p ON o.produce_id = p.id
    WHERE o.buyer_id = %s
    ORDER BY o.created_at DESC
    """

    cursor.execute(query, (buyer_id,))
    offers = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "buyer_id": buyer_id,
        "offers": offers
    }


@router.put("/{offer_id}/status")
def update_offer_status(
    offer_id: int,
    status: str,
    current_user=Depends(require_role("FARMER"))
):
    if status not in ["ACCEPTED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be ACCEPTED or REJECTED"
        )

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # Get offer
    query = """
    SELECT
        id,
        buyer_id,
        produce_id,
        quantity,
        offered_price,
        status
    FROM offers
    WHERE id = %s
    """

    cursor.execute(query, (offer_id,))
    offer = cursor.fetchone()

    if offer is None:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Offer not found"
        )

    if offer["status"] != "PENDING":
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Offer has already been processed"
        )

    # Check that the logged-in farmer owns the produce
    query = """
    SELECT
        farmer_id,
        quantity
    FROM produce
    WHERE id = %s
    """

    cursor.execute(
        query,
        (offer["produce_id"],)
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
            detail="You can only update offers for your own produce"
        )

    # Reject offer
    if status == "REJECTED":

        update_offer = """
        UPDATE offers
        SET status = %s
        WHERE id = %s
        """

        cursor.execute(
            update_offer,
            (
                "REJECTED",
                offer_id
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return {
            "message": "Offer rejected successfully",
            "offer_id": offer_id,
            "status": "REJECTED"
        }

    # Accept offer
    if float(offer["quantity"]) > float(produce["quantity"]):
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Not enough produce available"
        )

    # Reduce produce quantity
    update_produce = """
    UPDATE produce
    SET quantity = quantity - %s
    WHERE id = %s
    """

    cursor.execute(
        update_produce,
        (
            offer["quantity"],
            offer["produce_id"]
        )
    )

    # Calculate total order price
    total_price = (
        float(offer["quantity"])
        * float(offer["offered_price"])
    )

    # Create accepted order
    insert_order = """
    INSERT INTO orders
    (buyer_id, produce_id, quantity, total_price, status)
    VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(
        insert_order,
        (
            offer["buyer_id"],
            offer["produce_id"],
            offer["quantity"],
            total_price,
            "ACCEPTED"
        )
    )

    order_id = cursor.lastrowid

    # Mark offer as accepted
    update_offer = """
    UPDATE offers
    SET status = %s
    WHERE id = %s
    """

    cursor.execute(
        update_offer,
        (
            "ACCEPTED",
            offer_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Offer accepted and order created successfully",
        "offer_id": offer_id,
        "order_id": order_id,
        "total_price": total_price,
        "status": "ACCEPTED"
    }