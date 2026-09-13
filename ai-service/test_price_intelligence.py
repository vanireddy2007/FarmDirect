from price_intelligence import (
    calculate_price_intelligence,
    calculate_confidence,
    generate_explanation,
    recommend_selling_window
)


predicted_price = 2269
current_price = 2400

print("==============================")
print("PRICE INTELLIGENCE TEST")
print("==============================")

result = calculate_price_intelligence(predicted_price)

print("Predicted price: ₹", predicted_price)
print("Expected minimum: ₹", result["expected_min_price"])
print("Expected maximum: ₹", result["expected_max_price"])
print("Suggested minimum: ₹", result["suggested_minimum_price"])

confidence = calculate_confidence(predicted_price)

print("Confidence:", confidence)

explanation = generate_explanation(predicted_price)

print("Explanation:")
print(explanation)

selling_window = recommend_selling_window(
    current_price,
    predicted_price
)

print("Selling window:")
print(selling_window)

print("==============================")
print("TEST COMPLETED")
print("==============================")