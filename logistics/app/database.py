import os
import mysql.connector
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env')
load_dotenv(_env_path)


def get_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
