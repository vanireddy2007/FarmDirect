from buyer_matching import match_buyers


# ==================================================
# TEST FARMER
# ==================================================

farmer = {
    "crop": "Tomato",
    "quantity": 1000,
    "quality": "A",
    "location": "Hyderabad"
}


# ==================================================
# TEST BUYERS
# ==================================================

buyers = [
    {
        "name": "Hyderabad Fresh Mart",
        "crop": "Tomato",
        "quantity": 1200,
        "quality": "A",
        "distance": 15,
        "verified": True
    },

    {
        "name": "City Wholesale Market",
        "crop": "Tomato",
        "quantity": 800,
        "quality": "A",
        "distance": 8,
        "verified": True
    },

    {
        "name": "Hotel Green Leaf",
        "crop": "Tomato",
        "quantity": 1000,
        "quality": "A",
        "distance": 20,
        "verified": True
    },

    {
        "name": "Vegetable Traders",
        "crop": "Potato",
        "quantity": 1500,
        "quality": "A",
        "distance": 12,
        "verified": True
    },

    {
        "name": "Fresh Foods Ltd",
        "crop": "Tomato",
        "quantity": 2000,
        "quality": "B",
        "distance": 40,
        "verified": True
    },

    {
        "name": "Local Retailer",
        "crop": "Tomato",
        "quantity": 500,
        "quality": "B",
        "distance": 60,
        "verified": False
    }
]


# ==================================================
# RUN MATCHING
# ==================================================

matched_buyers = match_buyers(
    farmer,
    buyers
)


# ==================================================
# DISPLAY RESULTS
# ==================================================

print("BUYER MATCHING")
print("================")

print("Farmer crop:", farmer["crop"])
print("Farmer quantity:", farmer["quantity"], "kg")
print("Farmer quality:", farmer["quality"])
print("Location:", farmer["location"])

print("\nTOP BUYER RECOMMENDATIONS")
print("==========================")

for index, buyer in enumerate(matched_buyers, start=1):

    print(f"\n{index}. {buyer['name']}")

    print(
        "   Compatibility score:",
        buyer["score"],
        "/ 100"
    )

    print(
        "   Match level:",
        buyer["match_level"]
    )

    print(
        "   Distance:",
        buyer["distance"],
        "km"
    )

    print(
        "   Reasons:",
        ", ".join(buyer["reasons"])
    )