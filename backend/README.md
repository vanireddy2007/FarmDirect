## Backend

Run the backend from the `backend` directory:

```powershell
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

### AI price prediction

`POST /api/ai/predict-price` forwards the five caller-provided inputs to the
separate Member 4 service at `AI_SERVICE_URL/predict-price`. Set
`AI_SERVICE_URL` and `AI_SERVICE_TIMEOUT_SECONDS` in `backend/.env`.

Request JSON:

```json
{
	"lag_1_price": 100.0,
	"rolling_7_day_average": 98.5,
	"month": 9,
	"day_of_week": 3,
	"current_price": 101.0
}
```

The backend does not create or infer historical mandi values. Until an existing
FarmDirect data flow supplies them, the frontend or another trusted caller must
provide these five values.

The AI service is not present in this checkout. Run it from the Member 4
`ai-service` folder with:

```powershell
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8001
```
