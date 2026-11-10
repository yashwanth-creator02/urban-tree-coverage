"""
Unit tests for forecasting and trend projection.
"""

import numpy as np
from src.core.forecast import forecast_linear_trend


def test_forecast_rmse_loo():
    years = [2000, 2010, 2020, 2025]
    values = [30.0, 25.0, 20.0, 17.5]  # Perfect linear: slope = -0.5/year

    res = forecast_linear_trend(years, values, target_years=[2030])

    assert "rmse_loo" in res
    # Perfect linear should have near-zero LOO RMSE
    assert res["rmse_loo"] < 0.5
