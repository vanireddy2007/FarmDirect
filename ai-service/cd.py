import pandas as pd

data = pd.read_csv("data/download.csv")

print(data.head())
print("\nColumns:")
print(data.columns)