from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import time
import numpy as np
import pandas as pd
from binance import ThreadedWebsocketManager
from binance.client import Client
from sklearn.linear_model import LinearRegression

load_dotenv()  # Load the .env file
API_KEY = os.environ.get('BINANCE_FUTURES_TESTNET_API_KEY')
API_SECRET = os.environ.get('BINANCE_FUTURES_TESTNET_SK')


class StatArbCrypto():

    def __init__(self, symbolOne, symbolTwo, bar_length):
        self.client = Client(api_key=API_KEY, api_secret=API_SECRET,
                             tld="com", testnet=True)
        self.symbolOne = symbolOne
        self.symbolTwo = symbolTwo
        self.bar_length = bar_length
        self.units = 1  # Define default units
        self.leverage = 1  # Define default leverage
        self.trading_signal = 0  # -1, 0, 1 for short, neutral, long respectively
        self.cum_profits = 0  # initialize cumulative profits to 0

        self.preparedData = pd.DataFrame()
        self.comparePair = pd.DataFrame()

        self.twm = ThreadedWebsocketManager()

        self.dataOne = pd.DataFrame()
        self.dataTwo = pd.DataFrame()

        self.position = 0  # 1 for...

    def compute_hedge_ratio(self, y, x):
        # 1. Merge the two series on datetime index
        df = pd.DataFrame({
            'x': x,
            'y': y
        })

        # 2. Drop rows with NaN values to ensure alignment
        df.dropna(inplace=True)

        # 3. Extract the aligned series
        x_aligned = df['x'].values.reshape(-1, 1)
        y_aligned = df['y'].values

        model = LinearRegression().fit(x_aligned, y_aligned)
        return model.coef_[0]

    def compute_spread(self, y, x, hedge_ratio):
        return y - hedge_ratio * x

    def get_most_recent(self, symbol, interval, days):
        now = datetime.utcnow()
        past = str(now - timedelta(days=days))
        bars = self.client.futures_historical_klines(
            symbol=symbol, interval=interval, start_str=past, limit=1000)

        df = pd.DataFrame(bars)
        df.columns = [
            "open time", "open", "high", "low", "close", "volume", "close time",
            "quote asset Volume", "number of trades", "taker buy base asset volume",
            "taker buy quote asset volume", "ignore"
        ]
        df["date"] = pd.to_datetime(df["open time"], unit="ms")
        df = df[["date", "close",
                 "volume"]].copy()
        df.set_index("date", inplace=True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["complete"] = [True for row in range(len(df) - 1)] + [False]

        if symbol == self.symbolOne:
            self.dataOne = df
        else:
            self.dataTwo = df

    def start_trading(self, historical_days):
        print("Starting the Threaded Websocket Manager...")
        self.twm.start()
        print("Starting trading...")

        # Set leverage
        for symbol in [self.symbolOne, self.symbolTwo]:
            try:
                print(f"Setting leverage for {symbol}...")
                self.client.futures_change_leverage(
                    symbol=symbol, leverage=self.leverage)
                print(f"Leverage set for {symbol}.")

                print(f"Fetching historical data for {symbol}...")
                self.get_most_recent(symbol, self.bar_length, historical_days)
                print(f"Data fetched for {symbol}.")

                # Start streaming data
                print(f"Initializing kline futures socket for {symbol}...")
                self.twm.start_kline_futures_socket(
                    callback=self.stream_candles, symbol=symbol, interval=self.bar_length)
                print(f"Kline futures socket initialized for {symbol}.")
            except Exception as e:
                print(f"An error occurred while setting up for {symbol}: {e}")

        try:

            print("Threaded Websocket Manager started.")
            self.twm.join()
        except Exception as e:
            print(
                f"An error occurred with the Threaded Websocket Manager: {e}")

    def stream_candles(self, msg):
        # Extract required items from the message
        symbol = msg["ps"]  # Extracting symbol
        event_time = pd.to_datetime(msg["E"], unit="ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit="ms")
        close = float(msg["k"]["c"])
        volume = float(msg["k"]["v"])
        complete = msg["k"]["x"]

        # Determine which data to update
        if symbol == self.symbolOne:
            data_to_update = self.dataOne
        elif symbol == self.symbolTwo:
            data_to_update = self.dataTwo
        else:
            return  # If the symbol doesn't match, don't process further

        if event_time >= datetime(2023, 9, 21, 16, 55):
            hedge_ratio = self.compute_hedge_ratio(
                self.dataOne['close'], self.dataTwo['close'])
            self.twm.stop()

            # self.comparePair.reset_index(inplace=True)
            self.comparePair.to_csv('resultCompare.csv', index=True)

            # self.preparedData.reset_index(inplace=True)
            self.preparedData.to_csv('result.csv', index=True)

            if self.position in [1, -1]:  # If we have an active position
                side_one = "SELL" if self.position == 1 else "BUY"
                side_two = "BUY" if self.position == 1 else "SELL"
                order1 = self.client.futures_create_order(
                    symbol=self.symbolOne, side=side_one, type="MARKET", quantity=self.units)
                order2 = self.client.futures_create_order(
                    symbol=self.symbolTwo, side=side_two, type="MARKET", quantity=self.units * hedge_ratio)
                self.report_trade(order1, "GOING NEUTRAL AND STOP")
                self.report_trade(order2, "GOING NEUTRAL AND STOP")
                self.position = 0
            else:
                print("STOP")

        else:
            print(".", end="", flush=True)

            data_to_update.loc[start_time] = [
                close, volume, complete]

            # If the latest bar is complete, prepare features and define the strategy/trading positions
            if complete:
                self.define_strategy()
                self.execute_trades()

    def determine_signal(self, zscore):
        if zscore > 1.8:
            return -1  # Short spread
        elif zscore < -1.8:
            return 1   # Long spread
        else:
            return 0   # Neutral

    def define_strategy(self):
        try:
            # Create a copy of dataOne
            working_data = self.dataOne.copy()

            # Calculate hedge ratio
            self.hedge_ratio = self.compute_hedge_ratio(
                working_data['close'], self.dataTwo['close'])

            # Calculate the spread
            working_data['spread'] = self.compute_spread(
                working_data['close'], self.dataTwo['close'], self.hedge_ratio)

            # Calculate the running mean and standard deviation of the spread
            working_data['mean_spread'] = working_data['spread'].expanding().mean()
            working_data['std_spread'] = working_data['spread'].expanding().std()

            # Calculate z-score
            working_data['zscore'] = (
                working_data['spread'] - working_data['mean_spread']) / working_data['std_spread']

            # Determine trading signals based on z-score for each row
            working_data['trading_signal'] = working_data['zscore'].apply(
                self.determine_signal)

            self.comparePair = self.dataTwo.copy()
            self.preparedData = working_data

        except Exception as e:
            print(f"Error in define_strategy: {e}")

    def execute_trades(self):
        # Get the last row's trading signal
        last_signal = self.preparedData['trading_signal'].iloc[-1]

        if last_signal == 1 and self.position == 0:
            # Long spread: Buy stockOne and short stockTwo
            order1 = self.client.futures_create_order(
                symbol=self.symbolOne, side="BUY", type="MARKET", quantity=self.units)
            order2 = self.client.futures_create_order(
                symbol=self.symbolTwo, side="SELL", type="MARKET", quantity=self.units * self.hedge_ratio)
            self.report_trade(order1, "LONG SPREAD", self.symbolOne)
            self.report_trade(order2, "SHORT SPREAD", self.symbolTwo)
            self.position = 1

        elif last_signal == -1 and self.position == 0:
            # Short spread: Short stockOne and buy stockTwo
            order1 = self.client.futures_create_order(
                symbol=self.symbolOne, side="SELL", type="MARKET", quantity=self.units)
            order2 = self.client.futures_create_order(
                symbol=self.symbolTwo, side="BUY", type="MARKET", quantity=self.units * self.hedge_ratio)
            self.report_trade(order1, "SHORT SPREAD", self.symbolOne)
            self.report_trade(order2, "LONG SPREAD", self.symbolTwo)
            self.position = -1

        elif last_signal == 0 and self.position != 0:
            # Neutralize the position
            side_one = "SELL" if self.position == 1 else "BUY"
            side_two = "BUY" if self.position == 1 else "SELL"
            order1 = self.client.futures_create_order(
                symbol=self.symbolOne, side=side_one, type="MARKET", quantity=self.units)
            order2 = self.client.futures_create_order(
                symbol=self.symbolTwo, side=side_two, type="MARKET", quantity=self.units * self.hedge_ratio)
            self.report_trade(order1, "GOING NEUTRAL", self.symbolOne)
            self.report_trade(order2, "GOING NEUTRAL", self.symbolTwo)
            self.position = 0

    def report_trade(self, order, going, symbol):
        time.sleep(0.1)
        order_time = order["updateTime"]
        trades = self.client.futures_account_trades(
            symbol=symbol, startTime=order_time)

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
    leverage = 10

    bot = StatArbCrypto(symbolOne, symbolTwo, bar_length)
    bot.leverage = leverage  # setting the leverage if it's an attribute of the bot

    historical_days = 30
    bot.start_trading(historical_days)
