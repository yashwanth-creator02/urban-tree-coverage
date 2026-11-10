"""
Predictive trend forecasting for urban green cover trajectory.
"""

from typing import Any, Dict, List, Tuple
import numpy as np


def forecast_linear_trend(
    years: List[int],
    values: List[float],
    target_years: List[int] = None,
) -> Dict[str, Any]:
    """
    Computes ordinary least squares linear regression on historical values
    and projects future horizons.
    """
    if target_years is None:
        target_years = [2030, 2035]

    x = np.array(years, dtype=np.float64)
    y = np.array(values, dtype=np.float64)

    if len(x) < 2:
        raise ValueError("At least 2 historical data points required for linear forecasting.")

    # OLS slope and intercept
    n = len(x)
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)

    slope = float(ss_xy / ss_xx) if ss_xx != 0 else 0.0
    intercept = float(y_mean - slope * x_mean)

    # R-squared calculation
    y_pred_hist = slope * x + intercept
    ss_tot = np.sum((y - y_mean) ** 2)
    ss_res = np.sum((y - y_pred_hist) ** 2)
    r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0

    projections = {}
    for ty in target_years:
        projected_val = max(0.0, float(slope * ty + intercept))
        projections[str(ty)] = round(projected_val, 2)

    # Leave-one-out cross-validation RMSE
    rmse_loo = _leave_one_out_rmse(years, values)

    return {
        "slope_per_year": round(slope, 4),
        "intercept": round(intercept, 2),
        "r_squared": round(r_squared, 4),
        "rmse_loo": round(rmse_loo, 4),
        "historical": {str(yr): round(float(v), 2) for yr, v in zip(years, values)},
        "projections": projections,
        "method": "linear_trend",
        "limitation_note": "Linear extrapolation based on multi-decadal samples; external policy interventions or land saturation can alter actual future outcomes. RMSE from leave-one-out cross-validation reported for held-out accuracy.",
    }


def _leave_one_out_rmse(years: List[int], values: List[float]) -> float:
    """
    Computes root mean square error using leave-one-out cross-validation.
    Each historical point is held out, the model is fit on the rest, and
    the prediction error on the held-out point is recorded.
    """
    n = len(years)
    if n < 3:
        return float("nan")

    errors = []
    for i in range(n):
        train_years = [years[j] for j in range(n) if j != i]
        train_values = [values[j] for j in range(n) if j != i]
        test_year = years[i]
        test_value = values[i]

        x_train = np.array(train_years, dtype=np.float64)
        y_train = np.array(train_values, dtype=np.float64)
        x_mean = np.mean(x_train)
        y_mean = np.mean(y_train)
        ss_xy = np.sum((x_train - x_mean) * (y_train - y_mean))
        ss_xx = np.sum((x_train - x_mean) ** 2)
        slope = float(ss_xy / ss_xx) if ss_xx != 0 else 0.0
        intercept = float(y_mean - slope * x_mean)

        pred = slope * test_year + intercept
        errors.append(pred - test_value)

    return float(np.sqrt(np.mean(np.array(errors) ** 2)))
