import pandas as pd

data = pd.read_csv("data/farmdirect_sample_mandi_prices.csv")

print("First 5 rows:")
print(data.head())

print("\nColumns:")
print(data.columns.tolist())

print("\nNumber of rows and columns:")
print(data.shape)