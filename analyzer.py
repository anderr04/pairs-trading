import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import logging

logger = logging.getLogger(__name__)

class Analyzer:
    def __init__(self):
        pass

    def perform_cointegration_analysis(self, series_y: pd.Series, series_x: pd.Series) -> dict | None:
        """
        Performs the Engle-Granger two-step cointegration test.
        Y = β * X + α
        Spread = Y - β * X
        We test the Spread for stationarity using the Augmented Dickey-Fuller (ADF) test.
        """
        try:
            # Check length is sufficient
            if len(series_y) < 30 or len(series_y) != len(series_x):
                logger.warning("Insufficient or mismatched data length for cointegration.")
                return None

            # Step 1: OLS Regression to find the Hedge Ratio (β)
            x_with_const = sm.add_constant(series_x)
            model = sm.OLS(series_y, x_with_const).fit()
            
            # Hedge ratio is the slope (the coefficient for X)
            hedge_ratio = model.params.iloc[1] if isinstance(model.params, pd.Series) else model.params[1]
            
            # Calculate the Spread (residuals)
            spread = series_y - (hedge_ratio * series_x)
            
            # Step 2: ADF Test on the spread
            # Null hypothesis: The spread has a unit root (is non-stationary)
            adf_result = adfuller(spread, autolag='AIC')
            test_statistic = adf_result[0]
            p_value = adf_result[1]
            critical_value_5pct = adf_result[4]['5%']
            
            # Cointegrated if spread is stationary (reject null hypothesis at 5% confidence level)
            is_cointegrated = bool((p_value < 0.05) and (test_statistic < critical_value_5pct))
            
            # Compute Rolling or Static Z-Score
            # Here we use the static mean and std over the lookback period
            mean_spread = spread.mean()
            std_spread = spread.std()
            
            current_spread = spread.iloc[-1]
            z_score = (current_spread - mean_spread) / std_spread if std_spread > 0 else 0.0
            
            return {
                "is_cointegrated": is_cointegrated,
                "p_value": float(p_value),
                "hedge_ratio": float(hedge_ratio),
                "z_score": float(z_score),
                "current_spread": float(current_spread),
                "mean_spread": float(mean_spread),
                "std_spread": float(std_spread)
            }
            
        except Exception as e:
            logger.error(f"Error during cointegration analysis: {e}")
            return None
