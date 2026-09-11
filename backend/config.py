import os

from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://127.0.0.1:8001"
).rstrip("/")

AI_SERVICE_TIMEOUT_SECONDS = float(
    os.getenv("AI_SERVICE_TIMEOUT_SECONDS", "5")
)