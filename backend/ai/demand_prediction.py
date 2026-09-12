import numpy as np
from sklearn.linear_model import LinearRegression


def predict_demand(historical_demand, future_periods=1):

    if not historical_demand:
        raise ValueError("Historical demand data is required")

    if len(historical_demand) < 2:
        raise ValueError(
            "At least 2 historical demand values are required"
        )

    X = np.arange(
        1,
        len(historical_demand) + 1
    ).reshape(-1, 1)

    y = np.array(
        historical_demand,
        dtype=float
    )

    model = LinearRegression()

    model.fit(X, y)

    future_X = np.arange(
        len(historical_demand) + 1,
        len(historical_demand) + future_periods + 1
    ).reshape(-1, 1)

    predictions = model.predict(future_X)

    predictions = np.maximum(
        predictions,
        0
    )

    return predictions.tolist()