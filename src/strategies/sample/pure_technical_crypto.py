from dotenv import load_dotenv
import os
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from binance import ThreadedWebsocketManager
from binance.client import Client
import sys

from ...utils.technical_indicators import *

load_dotenv()  # Load the .env file
API_KEY = os.environ.get('BINANCE_PROD_API_KEY')
API_SECRET = os.environ.get('BINANCE_PROD_SK')


class PureTechnicalCrypto():

    def __init__(self, symbol, bar_length, units, position=0, leverage=5):

        self.symbol = symbol
        self.bar_length = bar_length
        self.units = units
        self.position = position
        self.leverage = leverage
        self.cum_profits = 0

    def start_trading(self, historical_days):

        client.futures_change_leverage(
            symbol=self.symbol, leverage=self.leverage)

        self.twm = ThreadedWebsocketManager()
        self.twm.start()

        self.get_most_recent(symbol=self.symbol, interval=self.bar_length,
                             days=historical_days)
        self.twm.start_kline_futures_socket(callback=self.stream_candles,
                                            symbol=self.symbol, interval=self.bar_length)  # Adj: start_kline_futures_socket
        self.twm.join()

        # "else" to be added later in the course

    def get_most_recent(self, symbol, interval, days):

        now = datetime.utcnow()
        past = str(now - timedelta(days=days))

        bars = client.futures_historical_klines(symbol=symbol, interval=interval,
                                                start_str=past, end_str=None, limit=1000)  # Adj: futures_historical_klines
        df = pd.DataFrame(bars)
        df["date"] = pd.to_datetime(df.iloc[:, 0], unit="ms")
        df.columns = ["open time", "open", "high", "low", "close", "volume",
                      "close time", "quote asset Volume", "number of trades",
                      "taker buy base asset volume", "taker buy quote asset volume", "ignore", "date"]
        df = df[["date", "open", "high", "low", "close", "volume"]].copy()
        df.set_index("date", inplace=True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["complete"] = [True for row in range(len(df)-1)] + [False]

        self.data = df

    def stream_candles(self, msg):

        # extract the required items from msg
        event_time = pd.to_datetime(msg["E"], unit="ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit="ms")
        first = float(msg["k"]["o"])
        high = float(msg["k"]["h"])
        low = float(msg["k"]["l"])
        close = float(msg["k"]["c"])
        volume = float(msg["k"]["v"])
        complete = msg["k"]["x"]

        # stop trading session
        if event_time >= datetime(2023, 9, 25, 17, 30):
            self.twm.stop()
            if self.position == 1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units)
                self.report_trade(order, "GOING NEUTRAL AND STOP")
                self.position = 0
            elif self.position == -1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units)
                self.report_trade(order, "GOING NEUTRAL AND STOP")
                self.position = 0
            else:
                print("STOP")

        else:
            # print out
            # just print something to get a feedback (everything OK)
            print(".", end="", flush=True)

            # feed df (add new bar / update latest bar)
            self.data.loc[start_time] = [
                first, high, low, close, volume, complete]

            # prepare features and define strategy/trading positions whenever the latest bar is complete
            if complete == True:
                self.define_strategy()
                self.execute_trades()

    def define_strategy(self):

        data = self.data.copy()

        # ******************** define your strategy here ************************
        data = relative_strength_index(data)
        data = macd(data)
        data = stochastic_oscillator(data)
        data = bollinger_bands(data)
        data = average_true_range(data)
        data = average_directional_index(data)

        data.dropna(inplace=True)

        adx_cond = data['adx'].iloc[-1] > 25

        # Buy Conditions
        bcond1 = (data['rsi'].shift(1) < 30) & (
            data['rsi'] > data['rsi'].shift(1))
        bcond2 = data['macd'] > data['signal']
        bcond3 = (data['%K'].shift(1) < data['%D'].shift(1)) & (
            data['%K'] < 20) & (data['%K'] > data['%D'])
        bcond4 = data['close'] <= data['lower_band']

        buy_cond = bcond1 & bcond2 & bcond3 & bcond4 & adx_cond

        # Sell Conditions
        scond1 = (data['rsi'].shift(1) > 70) & (
            data['rsi'] < data['rsi'].shift(1))
        scond2 = data['macd'] < data['signal']
        scond3 = (data['%K'].shift(1) > data['%D'].shift(1)) & (
            data['%K'] > 80) & (data['%K'] < data['%D'])
        scond4 = data['close'] >= data['upper_band']

        sell_cond = scond1 & scond2 & scond3 & scond4 & adx_cond

        data["position"] = 0
        data.loc[buy_cond, "position"] = 1
        data.loc[sell_cond, "position"] = -1

        self.prepared_data = data.copy()

    def execute_trades(self):
        # if position is long -> go/stay long
        if self.prepared_data["position"].iloc[-1] == 1:
            if self.position == 0:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units)
                self.report_trade(order, "GOING LONG")
            elif self.position == -1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=2 * self.units)
                self.report_trade(order, "GOING LONG")
            self.position = 1
        # if position is neutral -> go/stay neutral
        elif self.prepared_data["position"].iloc[-1] == 0:
            if self.position == 1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units)
                self.report_trade(order, "GOING NEUTRAL")
            elif self.position == -1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units)
                self.report_trade(order, "GOING NEUTRAL")
            self.position = 0
        # if position is short -> go/stay short
        if self.prepared_data["position"].iloc[-1] == -1:
            if self.position == 0:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units)
                self.report_trade(order, "GOING SHORT")
            elif self.position == 1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=2 * self.units)
                self.report_trade(order, "GOING SHORT")
            self.position = -1

    def report_trade(self, order, going):

        time.sleep(0.1)
        order_time = order["updateTime"]
        trades = client.futures_account_trades(
            symbol=self.symbol, startTime=order_time)
        order_time = pd.to_datetime(order_time, unit="ms")

        # extract data from trades object
        df = pd.DataFrame(trades)
        columns = ["qty", "quoteQty", "commission", "realizedPnl"]
        for column in columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        base_units = round(df.qty.sum(), 5)
        quote_units = round(df.quoteQty.sum(), 5)
        commission = -round(df.commission.sum(), 5)
        real_profit = round(df.realizedPnl.sum(), 5)
        price = round(quote_units / base_units, 5)

        # calculate cumulative trading profits
        self.cum_profits += round((commission + real_profit), 5)

        # print trade report
        print(2 * "\n" + 100 * "-")
        print("{} | {}".format(order_time, going))
        print("{} | Base_Units = {} | Quote_Units = {} | Price = {} ".format(
            order_time, base_units, quote_units, price))
        print("{} | Profit = {} | CumProfits = {} ".format(
            order_time, real_profit, self.cum_profits))
        print(100 * "-" + "\n")


if __name__ == "__main__":

    client = Client(api_key=API_KEY, api_secret=API_SECRET,
                    tld="com")

    symbol = "ETHUSDT"
    bar_length = "1m"
    units = 0.05
    position = 0
    leverage = 5

    trader = PureTechnicalCrypto(symbol=symbol, bar_length=bar_length,
                                 units=units,
                                 position=position, leverage=leverage)

    trader.start_trading(historical_days=1/24)
