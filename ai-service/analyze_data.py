import pandas as pd

data = pd.read_csv("data/farmdirect_sample_mandi_prices.csv")

print("PRICE SUMMARY:")
print(data[["minimum_price", "maximum_price", "modal_price"]].describe())

print("\nAVERAGE PRICES:")
print("Minimum:", data["minimum_price"].mean())
print("Maximum:", data["maximum_price"].mean())
print("Modal:", data["modal_price"].mean())

print("\nMISSING VALUES:")
print(data.isnull().sum())

#prize trend 
import matplotlib.pyplot as plt

data["date"] = pd.to_datetime(data["date"])

plt.plot(data["date"], data["modal_price"], marker="o")

plt.xlabel("Date")
plt.ylabel("Modal Price")
plt.title("Tomato Modal Price Trend")

plt.xticks(rotation=45)
plt.tight_layout()

plt.show()