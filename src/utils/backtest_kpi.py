import numpy as np
import pandas as pd

"""
A class for calculating key performance indicators (KPIs) of a backtest.

Args:
    returns_df (pandas.DataFrame): DataFrame with a 'Date' column and a 'Return' column.

Attributes:
    returns_df (pandas.DataFrame): DataFrame with daily returns.
"""


class BacktestKPI:

    def __init__(self, returns_df):
        self.returns_df = returns_df

    def compounded_annual_growth_rate(self, DF):
        "function to calculate the Cumulative Annual Growth Rate; DF should have return column"
        df = DF.copy()
        df["cumulative_return"] = (1 + df["return"]).cumprod()
        n = len(df)/252
        CAGR = (df["cumulative_return"].tolist()[-1])**(1/n) - 1
        return CAGR

    def sharpe(self, DF, rf=0.02):
        "function to calculate sharpe ratio ; rf is the risk free rate"
        df = DF.copy()
        sr = (self.CAGR(df) - rf)/volatility(df)
        return sr

    def calculate_max_drawdown(self):

        cum_returns = (1 + self.returns_df['Return']).cumprod()
        peak = cum_returns.max()
        trough = cum_returns.idxmin()
        max_drawdown = (peak - cum_returns[trough]) / peak
        return max_drawdown
