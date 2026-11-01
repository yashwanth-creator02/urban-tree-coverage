"""
Unit tests for forecasting and trend projection.
"""

import numpy as np
from src.core.forecast import forecast_linear_trend


def test_forecast_linear_trend():
    years = [2000, 2010, 2020]
    values = [30.0, 25.0, 20.0]  # Exact slope = -0.5 / year

    res = forecast_linear_trend(years, values, target_years=[2030])

    assert np.isclose(res["slope_per_year"], -0.5)
    assert np.isclose(res["r_squared"], 1.0)
    assert np.isclose(res["projections"]["2030"], 15.0)
