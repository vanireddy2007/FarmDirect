from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from backend.database import get_connection
from backend.security import hash_password, verify_password, create_access_token
router = APIRouter()


@router.post("/register")
def register_user(
    name: str,
    phone: str,
    password: str,
    role: str,
    location: str = "",
    language: str = ""
):
    connection = get_connection()
    cursor = connection.cursor()

    hashed_password = hash_password(password)

    query = """
    INSERT INTO users
    (name, phone, password, role, location, language)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            name,
            phone,
            hashed_password,
            role,
            location,
            language
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "User registered successfully"
    }


@router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    phone = form_data.username
    password = form_data.password
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        id,
        name,
        phone,
        password,
        role,
        location,
        language
    FROM users
    WHERE phone = %s
    """

    cursor.execute(query, (phone,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password"
        )

    if not verify_password(
        password,
        user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password"
        )

    access_token = create_access_token(
        {
            "sub": str(user["id"]),
            "role": user["role"]
        }
    )

    return {
        "message": "Login successful",

        "access_token": access_token,

        "token_type": "bearer",

        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": user["phone"],
            "role": user["role"],
            "location": user["location"],
            "language": user["language"]
        }
    }