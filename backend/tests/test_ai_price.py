import httpx
import pytest
from fastapi.testclient import TestClient

from main import app
from routers import ai
from services.ai_client import (
    AIServiceError,
    PricePredictionRequest,
    predict_price,
)


client = TestClient(app)

VALID_REQUEST = {
    "lag_1_price": 100.0,
    "rolling_7_day_average": 98.5,
    "month": 9,
    "day_of_week": 3,
    "current_price": 101.0,
}

VALID_RESPONSE = {
    "predicted_price": 104.25,
    "expected_min_price": 99.0,
    "expected_max_price": 110.0,
    "suggested_minimum_price": 100.5,
    "confidence": 0.87,
    "explanation": "Prices are expected to rise slightly.",
    "selling_window": "next 3 days",
    "disclaimer": "This is an estimate.",
}


def test_predict_price_forwards_inputs_and_returns_prediction(monkeypatch):
    captured = {}

    def fake_predict_price(request):
        captured.update(request.model_dump())
        return VALID_RESPONSE

    monkeypatch.setattr(ai, "predict_price", fake_predict_price)

    response = client.post("/api/ai/predict-price", json=VALID_REQUEST)

    assert response.status_code == 200
    assert captured == VALID_REQUEST
    assert response.json() == VALID_RESPONSE


def test_predict_price_rejects_invalid_input():
    response = client.post(
        "/api/ai/predict-price",
        json={**VALID_REQUEST, "day_of_week": 7}
    )

    assert response.status_code == 422


def test_predict_price_returns_service_unavailable(monkeypatch):
    def unavailable(_request):
        raise AIServiceError("AI price prediction service is unavailable")

    monkeypatch.setattr(ai, "predict_price", unavailable)

    response = client.post("/api/ai/predict-price", json=VALID_REQUEST)

    assert response.status_code == 503
    assert response.json()["detail"] == "AI price prediction service is unavailable"


def test_client_forwards_five_fields_and_returns_prediction(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return VALID_RESPONSE

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", lambda timeout: FakeClient())

    result = predict_price(PricePredictionRequest(**VALID_REQUEST))

    assert captured["url"].endswith("/predict-price")
    assert captured["json"] == VALID_REQUEST
    assert result.predicted_price == VALID_RESPONSE["predicted_price"]


def test_client_rejects_malformed_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"predicted_price": 1}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", lambda timeout: FakeClient())

    with pytest.raises(AIServiceError, match="invalid response"):
        predict_price(PricePredictionRequest(**VALID_REQUEST))


def test_client_translates_timeout_to_service_error(monkeypatch):
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "Client", lambda timeout: FakeClient())

    with pytest.raises(AIServiceError, match="unavailable"):
        predict_price(PricePredictionRequest(**VALID_REQUEST))