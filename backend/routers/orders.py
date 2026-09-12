from fastapi import APIRouter, HTTPException, Depends
from database import get_connection
from role_dependency import require_role

router = APIRouter()


@router.post("/place")
def place_order(
    current_user=Depends(require_role("BUYER")),
    produce_id: int = 0,
    quantity: float = 0
):
    buyer_id = current_user["user_id"]

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT id, quantity, expected_price
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

    total_price = quantity * float(produce["expected_price"])

    insert_query = """
    INSERT INTO orders
    (buyer_id, produce_id, quantity, total_price)
    VALUES (%s, %s, %s, %s)
    """

    cursor.execute(
        insert_query,
        (
            buyer_id,
            produce_id,
            quantity,
            total_price
        )
    )

    connection.commit()

    order_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return {
        "message": "Order placed successfully",
        "order_id": order_id,
        "buyer_id": buyer_id,
        "total_price": total_price
    }


@router.get("/buyer/{buyer_id}")
def get_buyer_orders(buyer_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        o.id AS order_id,
        o.buyer_id,
        o.produce_id,
        p.crop_name,
        o.quantity,
        p.unit,
        o.total_price,
        o.status,
        o.created_at
    FROM orders o
    JOIN produce p ON o.produce_id = p.id
    WHERE o.buyer_id = %s
    ORDER BY o.created_at DESC
    """

    cursor.execute(query, (buyer_id,))
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "buyer_id": buyer_id,
        "orders": orders
    }


@router.get("/farmer/{farmer_id}")
def get_farmer_orders(farmer_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        o.id AS order_id,
        o.buyer_id,
        o.produce_id,
        p.crop_name,
        o.quantity,
        p.unit,
        o.total_price,
        o.status,
        o.created_at
    FROM orders o
    JOIN produce p ON o.produce_id = p.id
    WHERE p.farmer_id = %s
    ORDER BY o.created_at DESC
    """

    cursor.execute(query, (farmer_id,))
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "farmer_id": farmer_id,
        "orders": orders
    }


@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
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

    query = """
    SELECT
        id,
        produce_id,
        quantity,
        status
    FROM orders
    WHERE id = %s
    """

    cursor.execute(query, (order_id,))
    order = cursor.fetchone()

    if order is None:
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order["status"] != "PENDING":
        cursor.close()
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Order has already been processed"
        )

    # Check that the logged-in farmer owns the produce
    query = """
    SELECT farmer_id, quantity
    FROM produce
    WHERE id = %s
    """

    cursor.execute(
        query,
        (order["produce_id"],)
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
            detail="You can only update orders for your own produce"
        )

    if status == "ACCEPTED":

        if float(order["quantity"]) > float(produce["quantity"]):
            cursor.close()
            connection.close()
            raise HTTPException(
                status_code=400,
                detail="Not enough produce available"
            )

        update_produce = """
        UPDATE produce
        SET quantity = quantity - %s
        WHERE id = %s
        """

        cursor.execute(
            update_produce,
            (
                order["quantity"],
                order["produce_id"]
            )
        )

    update_order = """
    UPDATE orders
    SET status = %s
    WHERE id = %s
    """

    cursor.execute(
        update_order,
        (
            status,
            order_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Order status updated successfully",
        "order_id": order_id,
        "status": status
    }