from fastapi import FastAPI
from pydantic import BaseModel
from buyer_matching import match_buyers


app = FastAPI(
    title="FarmDirect Buyer Matching AI",
    description="AI service for matching farmers with suitable buyers",
    version="1.0"
)


# ------------------------------------------
# REQUEST DATA MODELS
# ------------------------------------------

class Farmer(BaseModel):
    crop: str
    quantity: float
    quality: str
    location: str


class Buyer(BaseModel):
    name: str
    crop: str
    quantity: float
    quality: str
    distance: float
    verified: bool


class BuyerMatchingRequest(BaseModel):
    farmer: Farmer
    buyers: list[Buyer]


# ------------------------------------------
# HOME
# ------------------------------------------

@app.get("/")
def home():
    return {
        "message": "FarmDirect Buyer Matching AI is running!"
    }


# ------------------------------------------
# BUYER MATCHING API
# ------------------------------------------

@app.post("/match-buyers")
def match_farmer_with_buyers(
    request: BuyerMatchingRequest
):

    farmer = request.farmer.model_dump()
    buyers = [
        buyer.model_dump()
        for buyer in request.buyers
    ]

    matched_buyers = match_buyers(
        farmer,
        buyers
    )

    return {
        "farmer": farmer,
        "matched_buyers": matched_buyers
    }