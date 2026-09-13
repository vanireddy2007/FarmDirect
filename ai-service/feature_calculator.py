import pandas as pd


DATA_FILE = "data/dataset/farmdirect_corrected_ml_data.csv"


def get_market_features(commodity, market, current_price):
    """
    Get the recent market information required by the ML model.
    """

    data = pd.read_csv(DATA_FILE)

    # Clean input text
    commodity = commodity.strip()
    market = market.strip()

    # Find matching crop and market
    filtered = data[
        (data["Commodity"].str.lower() == commodity.lower())
        & (data["Market"].str.lower() == market.lower())
    ].copy()

    if filtered.empty:
        raise ValueError(
            f"No mandi data found for {commodity} at {market}"
        )

    # Sort by date
    filtered["Price Date"] = pd.to_datetime(
        filtered["Price Date"]
    )

    filtered = filtered.sort_values("Price Date")

    # Most recent previous market price
    lag_1_price = float(
        filtered.iloc[-1]["Modal Price"]
    )

    # Last 7 calendar days of available data
    latest_date = filtered["Price Date"].max()

    seven_day_data = filtered[
        filtered["Price Date"]
        >= latest_date - pd.Timedelta(days=7)
    ]

    rolling_7_day_average = float(
        seven_day_data["Modal Price"].mean()
    )

    # Current date features
    current_date = pd.Timestamp.today()

    month = int(current_date.month)
    day_of_week = int(current_date.dayofweek)

    return {
        "commodity": commodity,
        "market": market,
        "current_price": float(current_price),
        "lag_1_price": round(lag_1_price, 2),
        "rolling_7_day_average": round(
            rolling_7_day_average, 2
        ),
        "month": month,
        "day_of_week": day_of_week
    }