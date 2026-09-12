import pytest

from logistics.app.database import get_connection

TEST_FARMER_ID = 2
TEST_FPO_ID = "6"


def _insert_produce(crop, quantity, quality="Grade A", price=20.0, location="Sangareddy"):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO produce (farmer_id, crop_name, quantity, unit, quality, expected_price, location, available_date)
        VALUES (%s, %s, %s, 'kg', %s, %s, %s, CURDATE())
        """,
        (TEST_FARMER_ID, crop, quantity, quality, price, location),
    )
    connection.commit()
    produce_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return str(produce_id)


def _delete_produce(produce_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM produce WHERE id = %s", (produce_id,))
    connection.commit()
    cursor.close()
    connection.close()


@pytest.fixture
def make_test_produce():
    created_ids = []

    def _make(crop, quantity, quality="Grade A", price=20.0, location="Sangareddy"):
        produce_id = _insert_produce(crop, quantity, quality, price, location)
        created_ids.append(produce_id)
        return produce_id

    yield _make

    for produce_id in created_ids:
        _delete_produce(produce_id)
