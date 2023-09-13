import numpy as np
import pandas as pd


def max_drawdown(df):
    cum_returns = (1 + df['returns']).cumprod()
    max_return = cum_returns.cummax()
    drawdown = (cum_returns / max_return) - 1
    return drawdown.min()


def sharpe_ratio(df, risk_free_rate=0.03):
    expected_return = df['returns'].mean() * 252
    volatility = df['returns'].std() * (252 ** 0.5)
    return (expected_return - risk_free_rate) / volatility


def sortino_ratio(df, risk_free_rate=0.03):
    expected_return = df['returns'].mean() * 252
    downside_volatility = df[df['log_returreturnsns'] < 0]['returns'].std(
    ) * (252 ** 0.5)  # Annualized downside volatility
    return (expected_return - risk_free_rate) / downside_volatility


def treynor_ratio(df, beta, risk_free_rate=0.03):
    expected_return = df['returns'].mean() * 252
    return (expected_return - risk_free_rate) / beta
