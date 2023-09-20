from dotenv import load_dotenv
import os
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from binance import ThreadedWebsocketManager
from binance.client import Client
import sys
from sklearn.linear_model import LinearRegression


load_dotenv()  # Load the .env file
API_KEY = os.environ.get('BINANCE_FUTURES_TESTNET_API_KEY')
API_SECRET = os.environ.get('BINANCE_FUTURES_TESTNET_SK')


class StatArbCrypto():

    def __init__(self, symbolOne, symbolTwo, bar_length, units, position=0, leverage=3):
        self.client = Client(
            api_key=API_KEY, api_secret=API_SECRET, tld="com", testnet=True)
        self.symbolOne = symbolOne
        self.symbolTwo = symbolTwo
        self.bar_length = bar_length
        self.units = units
        self.position = position
        self.leverage = leverage
        self.cum_profits = 0

        self.dataOne = pd.DataFrame()
        self.dataTwo = pd.DataFrame()

    def start_trading(self, historical_days):
        # Setting leverage for both symbols
        self.client.futures_change_leverage(
            symbol=self.symbolOne, leverage=self.leverage)
        self.client.futures_change_leverage(
            symbol=self.symbolTwo, leverage=self.leverage)

        self.twm = ThreadedWebsocketManager()
        self.twm.start()

        # Getting most recent data for both symbols
        self.get_most_recent(interval=self.bar_length, days=historical_days)

        # Starting kline futures sockets for both symbols
        self.twm.start_kline_futures_socket(
            callback=self.stream_candles, symbol=self.symbolOne, interval=self.bar_length)
        self.twm.start_kline_futures_socket(
            callback=self.stream_candles, symbol=self.symbolTwo, interval=self.bar_length)

        self.twm.join()

    def get_most_recent(self, interval, days):
        self.dataOne = self.get_data_for_symbol(self.symbolOne, interval, days)
        self.dataTwo = self.get_data_for_symbol(self.symbolTwo, interval, days)

    def get_data_for_symbol(self, symbol, interval, days):
        now = datetime.utcnow()
        past = str(now - timedelta(days=days))
        bars = self.client.futures_historical_klines(
            symbol=symbol, interval=interval, start_str=past, limit=1000)
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

        return df

    def stream_candles(self, msg):
        # extract the required items from msg
        symbol = msg["ps"]  # Extracting symbol
        event_time = pd.to_datetime(msg["E"], unit="ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit="ms")
        first = float(msg["k"]["o"])
        high = float(msg["k"]["h"])
        low = float(msg["k"]["l"])
        close = float(msg["k"]["c"])
        volume = float(msg["k"]["v"])
        complete = msg["k"]["x"]

        # decide which data to update
        if symbol == self.symbolOne:
            data_to_update = self.dataOne
        elif symbol == self.symbolTwo:
            data_to_update = self.dataTwo
        else:
            return  # symbol doesn't match, so we don't process further

        data_to_update.loc[start_time] = [
            first, high, low, close, volume, complete]

        print(data_to_update)

        if event_time >= datetime(2023, 9, 25, 17, 30):
            hedge_ratio = self.compute_hedge_ratio(
                self.dataOne['close'], self.dataTwo['close'])
            self.twm.stop()
            if self.position == 1:
                # Neutralize both symbols when stopping
                order1 = self.client.futures_create_order(
                    symbol=self.symbolOne, side="SELL", type="MARKET", quantity=self.units)
                order2 = self.client.futures_create_order(
                    symbol=self.symbolTwo, side="BUY", type="MARKET", quantity=self.units * hedge_ratio)
                self.report_trade(order1, "GOING NEUTRAL AND STOP")
                self.report_trade(order2, "GOING NEUTRAL AND STOP")
                self.position = 0
            elif self.position == -1:
                # Neutralize both symbols when stopping
                order1 = self.client.futures_create_order(
                    symbol=self.symbolOne, side="BUY", type="MARKET", quantity=self.units)
                order2 = self.client.futures_create_order(
                    symbol=self.symbolTwo, side="SELL", type="MARKET", quantity=self.units * hedge_ratio)
                self.report_trade(order1, "GOING NEUTRAL AND STOP")
                self.report_trade(order2, "GOING NEUTRAL AND STOP")
                self.position = 0
            else:
                print("STOP")

        else:
            # print out
            # just print something to get a feedback (everything OK)
            print(".", end="", flush=True)

            # feed df (add new bar / update latest bar)
            data_to_update.loc[start_time] = [
                first, high, low, close, volume, complete]
            # prepare features and define strategy/trading positions whenever the latest bar is complete
            if complete == True:
                self.define_strategy()
                self.execute_trades()

    def compute_hedge_ratio(self, y, x):
        x = x.values.reshape(-1, 1)
        model = LinearRegression()
        model.fit(x, y)
        return model.coef_[0]

    def compute_spread(self, y, x, hedge_ratio):
        return y - hedge_ratio * x

    def define_strategy(self):
        hedge_ratio = self.compute_hedge_ratio(
            self.dataOne['close'], self.dataTwo['close'])
        self.dataOne['spread'] = self.compute_spread(
            self.dataOne['close'], self.dataTwo['close'], hedge_ratio)

        mean_spread = self.dataOne['spread'].mean()
        std_spread = self.dataOne['spread'].std()

        self.dataOne['zscore'] = (
            self.dataOne['spread'] - mean_spread) / std_spread

        self.dataOne['position'] = 0
        self.dataOne.loc[self.dataOne['zscore']
                         > 2, 'position'] = -1  # Short spread
        self.dataOne.loc[self.dataOne['zscore']
                         < -2, 'position'] = 1  # Long spread

        latest_row = self.dataOne.iloc[-1]
        print(latest_row)

    def execute_trades(self):

        hedge_ratio = self.compute_hedge_ratio(
            self.dataOne['close'], self.dataTwo['close'])
        # If position is long the spread -> Buy symbol1 and Sell symbol2
        if self.dataOne["position"].iloc[-1] == 1:
            # Buy symbol1
            order1 = self.client.futures_create_order(
                symbol=self.symbolOne, side="BUY", type="MARKET", quantity=self.units)
            self.report_trade(order1, f"GOING LONG {self.symbolOne}")

            # Sell (short) symbol2
            order2 = self.client.futures_create_order(
                symbol=self.symbolTwo, side="SELL", type="MARKET", quantity=self.units * hedge_ratio)  # Assuming units*hedgeratio doesn't break lot size constraints
            self.report_trade(order2, f"GOING SHORT {self.symbolTwo}")

        # If position is neutral -> neutralize positions for both symbols
        elif self.dataOne["position"].iloc[-1] == 0:
            if self.position == 1:
                # Neutralize previous positions
                self.report_trade(self.client.futures_create_order(
                    symbol=self.symbolOne, side="SELL", type="MARKET", quantity=self.units), f"GOING NEUTRAL {self.symbolOne}")
                self.report_trade(self.client.futures_create_order(
                    symbol=self.symbolTwo, side="BUY", type="MARKET", quantity=self.units * hedge_ratio), f"GOING NEUTRAL {self.symbolTwo}")

            elif self.position == -1:
                # Neutralize previous positions
                self.report_trade(self.client.futures_create_order(
                    symbol=self.symbolOne, side="BUY", type="MARKET", quantity=self.units), f"GOING NEUTRAL {self.symbolOne}")
                self.report_trade(self.client.futures_create_order(
                    symbol=self.symbolTwo, side="SELL", type="MARKET", quantity=self.units * hedge_ratio), f"GOING NEUTRAL {self.symbolTwo}")

        # If position is short the spread -> Sell symbol1 and Buy symbol2
        elif self.dataOne["position"].iloc[-1] == -1:
            # Sell (short) symbol1
            order1 = self.client.futures_create_order(
                symbol=self.symbolOne, side="SELL", type="MARKET", quantity=self.units)
            self.report_trade(order1, f"GOING SHORT {self.symbolOne}")

            # Buy symbol2
            order2 = self.client.futures_create_order(
                symbol=self.symbolTwo, side="BUY", type="MARKET", quantity=self.units * hedge_ratio)  # Assuming units*hedgeratio doesn't break lot size constraints
            self.report_trade(order2, f"GOING LONG {self.symbolTwo}")

    def report_trade(self, order, going):

        time.sleep(0.1)
        order_time = order["updateTime"]
        trades = self.client.futures_account_trades(
            symbol=self.symbol, startTime=order_time)
        order_time = pd.to_datetime(order_time, unit="ms")

        # extract data from trades object
        df = pd.DataFrame(trades)
        print(df)
        columns = ["qty", "quoteQty", "commission", "realizedPnl"]
        for column in columns:
            try:
                df[column] = pd.to_numeric(df[column], errors="coerce")
            except KeyError:
                print(f"Column '{column}' not found in the DataFrame!")
                return
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
    symbolOne = "XRPUSDT"
    symbolTwo = "THETAUSDT"
    bar_length = "1h"
    units = 0.5
    position = 0
    leverage = 10

    trader = StatArbCrypto(symbolOne=symbolOne, symbolTwo=symbolTwo, bar_length=bar_length,
                           units=units, position=position, leverage=leverage)

    trader.start_trading(historical_days=1/24)
