# ==================================================
# BUYER MATCHING
# ==================================================


def calculate_buyer_score(
    crop_match,
    quantity_match,
    distance_match,
    quality_match,
    verification_match
):
    """
    Calculate buyer compatibility score.

    Weights:
    Crop compatibility       = 30%
    Quantity compatibility   = 25%
    Location proximity       = 20%
    Quality compatibility    = 15%
    Buyer verification       = 10%
    """

    score = (
        crop_match * 0.30
        + quantity_match * 0.25
        + distance_match * 0.20
        + quality_match * 0.15
        + verification_match * 0.10
    )

    return round(score, 2)


def get_match_level(score):
    """
    Convert compatibility score into
    an easy-to-understand recommendation level.
    """

    if score >= 90:
        return "Excellent Match"

    elif score >= 75:
        return "Good Match"

    elif score >= 50:
        return "Possible Match"

    else:
        return "Low Match"


def match_buyers(farmer, buyers):
    """
    Match one farmer with multiple buyers.

    Returns the top 5 buyers based on
    compatibility score.
    """

    results = []

    for buyer in buyers:

        # ------------------------------------------
        # 1. CROP COMPATIBILITY - 30%
        # ------------------------------------------

        if farmer["crop"].lower() != buyer["crop"].lower():
            continue

        crop_match = 100

        # ------------------------------------------
        # 2. QUANTITY COMPATIBILITY - 25%
        # ------------------------------------------

        if buyer["quantity"] >= farmer["quantity"]:
            quantity_match = 100

        else:
            quantity_match = (
                buyer["quantity"] / farmer["quantity"]
            ) * 100

        quantity_match = min(quantity_match, 100)

        # ------------------------------------------
        # 3. LOCATION PROXIMITY - 20%
        # ------------------------------------------

        distance = buyer["distance"]

        if distance <= 10:
            distance_match = 100

        elif distance <= 25:
            distance_match = 80

        elif distance <= 50:
            distance_match = 60

        else:
            distance_match = 30

        # ------------------------------------------
        # 4. QUALITY COMPATIBILITY - 15%
        # ------------------------------------------

        if farmer["quality"].lower() == buyer["quality"].lower():
            quality_match = 100

        else:
            quality_match = 50

        # ------------------------------------------
        # 5. BUYER VERIFICATION - 10%
        # ------------------------------------------

        if buyer["verified"]:
            verification_match = 100

        else:
            verification_match = 0

        # ------------------------------------------
        # CALCULATE FINAL SCORE
        # ------------------------------------------

        score = calculate_buyer_score(
            crop_match,
            quantity_match,
            distance_match,
            quality_match,
            verification_match
        )

        # ------------------------------------------
        # MATCH LEVEL
        # ------------------------------------------

        match_level = get_match_level(score)

        # ------------------------------------------
        # GENERATE REASONS
        # ------------------------------------------

        reasons = []

        reasons.append("Crop compatible")

        if quantity_match >= 80:
            reasons.append("Quantity compatible")

        elif quantity_match > 0:
            reasons.append("Partial quantity match")

        if distance <= 25:
            reasons.append("Nearby buyer")

        elif distance <= 50:
            reasons.append("Moderate distance")

        else:
            reasons.append("Farther buyer")

        if quality_match == 100:
            reasons.append("Quality compatible")

        else:
            reasons.append("Quality partially compatible")

        if buyer["verified"]:
            reasons.append("Verified buyer")

        else:
            reasons.append("Buyer not verified")

        # ------------------------------------------
        # STORE RESULT
        # ------------------------------------------

        results.append({
            "name": buyer["name"],
            "score": score,
            "match_level": match_level,
            "distance": distance,
            "reasons": reasons
        })

    # ------------------------------------------
    # SORT BY SCORE
    # ------------------------------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ------------------------------------------
    # RETURN TOP 5
    # ------------------------------------------

    return results[:5]