
from dotenv import load_dotenv
import os
from ibapi.order import Order
from ibapi.contract import Contract
from ib_insync import *
import pandas as pd
import time
import nasdaqdatalink
from datetime import datetime, timedelta
import numpy as np


def average_true_range(DF, n=14):
    df = DF.copy()
    df['H-L'] = abs(df['high']-df['low'])
    df['H-PC'] = abs(df['high']-df['close'].shift(1))
    df['L-PC'] = abs(df['low']-df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].ewm(com=n, min_periods=n).mean()
    df.drop(columns=['H-L', 'H-PC', 'L-PC', 'TR'], inplace=True)
    return df


NASDAQ_KEY = os.getenv("NASDAQ_KEY")
nasdaqdatalink.ApiConfig.api_key = NASDAQ_KEY

ticker = 'SOFI'

# Connect to the Interactive Brokers Gateway/TWS
ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)


contract = Stock(ticker, 'SMART', 'USD')

# Grab prices
prices = nasdaqdatalink.get_table(
    'SHARADAR/SEP', date={'gte': '2023-01-01'}, ticker=ticker)
prices_df = pd.DataFrame(prices[::-1])
prices_df["log_returns"] = np.log(prices_df.close / prices_df.close.shift(1))

atr_df = average_true_range(prices_df)
last_row_atr = atr_df.iloc[-1]
last_row_atr


def BracketOrder(parentOrderId: int, action: str, quantity: float,
                 limitPrice: float, takeProfitLimitPrice: float,
                 stopLossPrice: float):

    # This will be our main or "parent" order
    parent = Order()
    parent.orderId = parentOrderId
    parent.action = action
    parent.orderType = "LMT"
    parent.totalQuantity = quantity
    parent.lmtPrice = limitPrice
    # The parent and children orders will need this attribute set to False to prevent accidental executions.
    # The LAST CHILD will have it set to True,
    parent.transmit = False

    takeProfit = Order()
    takeProfit.orderId = parent.orderId + 1
    takeProfit.action = "SELL" if action == "BUY" else "BUY"
    takeProfit.orderType = "LMT"
    takeProfit.totalQuantity = quantity
    takeProfit.lmtPrice = takeProfitLimitPrice
    takeProfit.parentId = parentOrderId
    takeProfit.transmit = False

    stopLoss = Order()
    stopLoss.orderId = parent.orderId + 2
    stopLoss.action = "SELL" if action == "BUY" else "BUY"
    stopLoss.orderType = "STP"
    # Stop trigger price
    stopLoss.auxPrice = stopLossPrice
    stopLoss.totalQuantity = quantity
    stopLoss.parentId = parentOrderId
    # In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True
    # to activate all its predecessors
    stopLoss.transmit = True

    bracketOrder = [parent, takeProfit, stopLoss]
    print(bracketOrder)
    return bracketOrder


bracket = BracketOrder(parentOrderId=ib.client.getReqId(),
                       action='BUY',
                       quantity=550,
                       limitPrice=8.79,
                       takeProfitLimitPrice=8.86 + last_row_atr['ATR'] * 2,
                       stopLossPrice=8.86 - last_row_atr['ATR'] * 1.5)
for o in bracket:

    order = ib.placeOrder(contract, o)
