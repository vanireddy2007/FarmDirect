from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.fpo import router as fpo_router
from .routers.logistics import router as logistics_router

app = FastAPI(title='FarmDirect Logistics API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health_check():
    return {'status': 'ok', 'service': 'FarmDirect Logistics'}


app.include_router(fpo_router)
app.include_router(logistics_router)

