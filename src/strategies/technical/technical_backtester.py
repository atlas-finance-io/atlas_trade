import pytz
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from technical_indicators import *
import datetime
from itertools import product
import warnings
warnings.filterwarnings("ignore")
plt.style.use("seaborn-v0_8")


class TechnicalBacktester():

    def __init__(self, exchange, symbol, trading_days, trading_costs):
        self.exchange = exchange
        self.symbol = symbol
        self.trading_days = trading_days
        self.data = self.fetch_prices()
        self.trading_costs = trading_costs
        self.trading_periods_year = (self.data['close'].count(
        ) / ((self.data.index[-1] - self.data.index[0]).days / 365.25))

    def fetch_prices(self):
        # Prepare empty dataframe for results
        df_prices = pd.DataFrame()

        # Calculate the end timestamp for the data fetching
        end_timestamp = self.exchange.milliseconds()
        since_timestamp = end_timestamp - self.trading_days * 24 * 60 * 60 * 1000

        while since_timestamp < end_timestamp:
            try:
                # Fetch OHLCV data
                ohlcv_one = self.exchange.fetch_ohlcv(
                    self.symbol, '1h', since=since_timestamp, limit=1000)

                # Create temporary dataframes to hold fetched data
                df_temp = pd.DataFrame(
                    ohlcv_one, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                df_temp = df_temp[['timestamp', 'close']]

                # Concatenate with the final dataframe
                df_prices = pd.concat([df_prices, df_temp])

                # Update the since_timestamp to the last timestamp fetched
                since_timestamp = df_prices['timestamp'].max(
                ) + (60 * 60 * 1000)  # Add one hour

            except Exception as e:
                print(f"Error in fetching prices: {e}")
                break

        df_prices.drop_duplicates(
            subset='timestamp', keep='first', inplace=True)
        df_prices.sort_values(by='timestamp', inplace=True)
        # Example usage:
        df_prices['date'] = pd.to_datetime(
            df_prices['timestamp'], unit='ms', utc=True)

        # Apply the conversion to the entire 'date' column
        df_prices['date'] = df_prices['date'].apply(self.convert_to_bali_time)
        df_prices.set_index('date', inplace=True)

        df_prices['returns'] = np.log(df_prices['close'] /
                                      df_prices['close'].shift(1))
        return df_prices

    # Assuming df_prices['date'] is in UTC
    def convert_to_bali_time(self, utc_datetime):
        utc_tz = pytz.utc
        # Central Indonesia Time (WITA)
        bali_tz = pytz.timezone('Asia/Makassar')

        # Convert UTC datetime to Bali time
        bali_datetime = utc_datetime.astimezone(bali_tz)

        return bali_datetime

    def visualize_prices(self):

        plt.figure(figsize=(12, 6))
        plt.plot(self.data.index, self.data['close'], label=self.symbol)

        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()

        plt.show()

    # ================================== Strategies ==========================================

    def test_macd_cross(self):
        data = self.data.copy()
        data = macd(data)
        # Generate signals
        data['position'] = 0
        data.loc[data['macd'] > data['signal'], 'position'] = 1  # Buy signal
        data.loc[data['macd'] < data['signal'],
                 'position'] = 0  # Sell/Exit signal

        data["trades"] = data.position.diff().fillna(0).abs()

        data['strategy'] = data['position'].shift(1) * data['returns']
        data['strategy'] = data['strategy'] + \
            data['trades'] * self.trading_costs

        # Calculate cumulative returns
        data['cum_returns'] = (1 + data['strategy']).cumprod()

        data.to_csv('macd_cross.csv', index=True)
        self.results = data

    # ================================== Performance ==========================================

    def print_performance(self):
        ''' Calculates and prints various Performance Metrics.
        '''

        data = self.results.copy()
        strategy_multiple = round(self.calculate_multiple(data.strategy), 6)
        bh_multiple = round(self.calculate_multiple(data.returns), 6)
        outperf = round(strategy_multiple - bh_multiple, 6)
        cagr = round(self.calculate_cagr(data.strategy), 6)
        ann_mean = round(self.calculate_annualized_mean(data.strategy), 6)
        ann_std = round(self.calculate_annualized_std(data.strategy), 6)
        sharpe = round(self.calculate_sharpe(data.strategy), 6)

        print(100 * "=")
        print("Technical Strategies | INSTRUMENT = {} ".format(
            self.symbol))
        print(100 * "-")
        print("PERFORMANCE MEASURES:")
        print("\n")
        print("Multiple (Strategy):         {}".format(strategy_multiple))
        print("Multiple (Buy-and-Hold):     {}".format(bh_multiple))
        print(38 * "-")
        print("Out-/Underperformance:       {}".format(outperf))
        print("\n")
        print("CAGR:                        {}".format(cagr))
        print("Annualized Mean:             {}".format(ann_mean))
        print("Annualized Std:              {}".format(ann_std))
        print("Sharpe Ratio:                {}".format(sharpe))

        print(100 * "=")

    def calculate_multiple(self, series):
        return np.exp(series.sum())

    def calculate_cagr(self, series):
        return np.exp(series.sum())**(1/((series.index[-1] - series.index[0]).days / 365.25)) - 1

    def calculate_annualized_mean(self, series):
        return series.mean() * self.trading_periods_year

    def calculate_annualized_std(self, series):
        return series.std() * np.sqrt(self.trading_periods_year)

    def calculate_sharpe(self, series):
        if series.std() == 0:
            return np.nan
        else:
            return self.calculate_cagr(series) / self.calculate_annualized_std(series)
