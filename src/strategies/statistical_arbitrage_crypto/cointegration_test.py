import pandas as pd
import numpy as np
import ccxt
import seaborn as sns
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import coint
from statsmodels.regression.rolling import RollingOLS
from statsmodels.tsa.stattools import adfuller
import statsmodels.api as sm


class CointegrationTest():

    def __init__(self, exchange, symbol_one, symbol_two, universe=[], lookback_days=120, lookback_window=500, zscore_window=30):
        self.exchange = exchange

        self.symbol_one = symbol_one
        self.symbol_two = symbol_two
        self.single_pair_data = None
        self.hedge_ratio = None

        self.universe = universe
        self.universe_data = None

        self.lookback_days = lookback_days
        self.lookback_window = lookback_window
        self.zscore_window = zscore_window
        self.cointegrated_pairs = []

    def fetch_single_pair_prices(self):
        # Prepare empty dataframe for results
        df_final = pd.DataFrame()

        # Calculate the end timestamp for the data fetching
        end_timestamp = self.exchange.milliseconds()
        since_timestamp = end_timestamp - self.lookback_days * 24 * 60 * 60 * 1000

        while since_timestamp < end_timestamp:
            try:
                # Fetch OHLCV data

                ohlcv_one = self.exchange.fetch_ohlcv(
                    self.symbol_one, '1h', since=since_timestamp)
                ohlcv_two = self.exchange.fetch_ohlcv(
                    self.symbol_two, '1h', since=since_timestamp)

                # Create temporary dataframes to hold fetched data
                df_one_temp = pd.DataFrame(
                    ohlcv_one, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_two_temp = pd.DataFrame(
                    ohlcv_two, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Merge dataframes
                df_temp = pd.merge(df_one_temp[['timestamp', 'close']], df_two_temp[[
                                   'timestamp', 'close']], on='timestamp', how='inner')
                df_temp.columns = ['timestamp',
                                   self.symbol_one, self.symbol_two]

                # Concatenate with the final dataframe
                df_final = pd.concat([df_final, df_temp])

                # Update the since_timestamp to the last timestamp fetched
                since_timestamp = df_final['timestamp'].max(
                ) + (60 * 60 * 1000)  # Add one hour

            except Exception as e:
                print(f"Error in fetching prices: {e}")
                break

        # Remove duplicates and sort the dataframe
        df_final.drop_duplicates(
            subset='timestamp', keep='first', inplace=True)
        df_final.sort_values(by='timestamp', inplace=True)

        # Calculate Hedge Ratio over period
        x = df_final[self.symbol_one]
        y = df_final[self.symbol_two]

        model = sm.OLS(y, sm.add_constant(x)).fit()
        hedge_ratio = model.params[1]
        print(f"Current Hedge Ratio: {hedge_ratio}")
        self.hedge_ratio = hedge_ratio

        self.single_pair_data = df_final

    def fetch_prices(self, symbol, look_back_days):
        # Prepare empty dataframe for results
        df_final = pd.DataFrame()

        # Calculate the end timestamp for the data fetching
        end_timestamp = self.exchange.milliseconds()
        since_timestamp = end_timestamp - look_back_days * 24 * 60 * 60 * 1000

        while since_timestamp < end_timestamp:
            try:
                # Fetch OHLCV data
                price_data = self.exchange.fetch_ohlcv(
                    symbol, '1h', since=since_timestamp, limit=1000)
                df = pd.DataFrame(price_data, columns=[
                                  'timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Concatenate with the final dataframe
                df_final = pd.concat([df_final, df])

                # Update the since_timestamp to the last timestamp fetched
                since_timestamp = df_final['timestamp'].max(
                ) + (60 * 60 * 1000)  # Add one hour

            except Exception as e:
                print(f"Error in fetching prices: {e}")
                break

        # Remove duplicates and sort the dataframe
        df_final.drop_duplicates(
            subset='timestamp', keep='first', inplace=True)
        df_final.sort_values(by='timestamp', inplace=True)

        return df_final

    def single_pair_cointegeration_check(self, recent_bars=2880):
        S1 = self.single_pair_data[self.symbol_one].tail(recent_bars)
        S2 = self.single_pair_data[self.symbol_two].tail(recent_bars)

        if len(S1) != len(S2):
            print(
                f"Mismatch for pairs: {self.symbol_one} and {self.symbol_two}")
            return

        result = coint(S1, S2)
        pvalue = result[1]

        if pvalue < 0.05:
            print(f"{self.symbol_one} and {self.symbol_two} potential cointegration")
        else:
            print(f"{self.symbol_one} and {self.symbol_two} is not cointegrated")

    def rolling_hedge_ratio(self, Y, X, lookback_window):
        # Add a constant to X to represent the intercept for the OLS regression
        X_with_const = sm.add_constant(X)

        # Initialize the hedge_ratios Series to store the results
        hedge_ratios = pd.Series(index=Y.index)

        # Perform the rolling regression and calculate the hedge ratio (beta coefficient)
        rolling_model = RollingOLS(Y, X_with_const, window=lookback_window)
        rolling_results = rolling_model.fit()

        # Extract the beta coefficients (hedge ratios) from the rolling regression results
        # Use 'params' and select the second column, which represents the beta coefficient
        # The index is aligned with Y so no shifting occurs
        hedge_ratios = rolling_results.params.iloc[:, 1]

        return hedge_ratios

    def generate_zscore(self):
        df = self.single_pair_data.copy()
        # df["rolling_hedge_ratio"] = self.rolling_hedge_ratio(
        #     df[self.symbol_two], df[self.symbol_one], self.lookback_window)
        df['calculated_spread'] = df[self.symbol_two] - \
            self.hedge_ratio * df[self.symbol_one]

        df['rolling_mean_spread'] = df['calculated_spread'].rolling(
            window=self.zscore_window).mean()
        df['rolling_std_spread'] = df['calculated_spread'].rolling(
            window=self.zscore_window).std()
        df['z_score'] = (df['calculated_spread'] -
                         df['rolling_mean_spread']) / df['rolling_std_spread']
        self.single_pair_data = df

    def fetch_all_pairs_prices(self):
        combined_prices_df = pd.DataFrame()

        for symbol in self.universe:
            prices = self.fetch_prices(symbol, 120)
            combined_prices_df[symbol] = prices['close']

        # Drop rows with any NaN values to ensure all series are aligned
        combined_prices_df.dropna(inplace=True)
        self.universe_data = combined_prices_df

    def find_cointegrated_pairs(self):
        n = self.universe_data.shape[1]
        keys = self.universe_data.columns
        cointegrated_pairs = []

        # Find Potential Longer Term Cointegration
        for i in range(n):
            for j in range(i+1, n):
                S1 = self.universe_data[keys[i]]
                S2 = self.universe_data[keys[j]]

                if len(S1) != len(S2):
                    print(f"Mismatch for pairs: {keys[i]} and {keys[j]}")
                    continue

                result = coint(S1, S2)
                pvalue = result[1]

                if pvalue < 0.05:
                    cointegrated_pairs.append((keys[i], keys[j]))
        self.cointegrated_pairs = cointegrated_pairs

    def filter_near_term_cointegration(self, recent_bars):

        recent_cointegration_pairs = []

        for pair in self.cointegrated_pairs:
            prices_one = self.universe_data[pair[0]].tail(recent_bars)
            prices_two = self.universe_data[pair[1]].tail(recent_bars)

            if len(prices_one) != len(prices_two):
                print(f"Mismatch for pairs: {prices_one} and {prices_two}")
                continue

            result = coint(prices_one, prices_two)
            pvalue = result[1]

            if pvalue < 0.05:
                recent_cointegration_pairs.append((pair[0], pair[1]))

        self.cointegrated_pairs = recent_cointegration_pairs

    def plot_spread(self):
        plt.figure(figsize=(14, 7))
        plt.plot(self.single_pair_data.index,
                 self.single_pair_data['calculated_spread'], label='Calculated Spread')
        plt.axhline(
            self.single_pair_data['calculated_spread'].mean(), color='black')
        plt.legend(['Spread'])
        plt.show()

    def plot_zscore(self):
        plt.figure(figsize=(14, 7))
        plt.plot(self.single_pair_data.index,
                 self.single_pair_data['z_score'], label='Z-Score')
        plt.axhline(0, color='black', linestyle='--',
                    linewidth=2, label='Mean')
        plt.axhline(1.96, color='red', linestyle='--',
                    linewidth=2, label='Upper Threshold (2 std)')
        plt.axhline(-1.96, color='green', linestyle='--',
                    linewidth=2, label='Lower Threshold (-2 std)')
        plt.title('Z-Score Over Time')
        plt.xlabel('Date')
        plt.ylabel('Z-Score')
        plt.legend(loc='best')
        plt.show()

    def stationary_check(self):
        spread = self.single_pair_data['calculated_spread'].dropna()
        adf_result = adfuller(spread)
        print("ADF RESULT: ", adf_result[1])
        if adf_result[1] < 0.05:
            print("Null hypothesis that the spread is not stationary cannot be rejected ")
            return True
        else:
            print("The spread is not stationary.")
            return False

    def visualize_prices(self):
        # Convert 'timestamp' to datetime
        self.single_pair_data['timestamp'] = pd.to_datetime(
            self.single_pair_data['timestamp'], unit='ms')

        # Set 'timestamp' as the index
        self.single_pair_data.set_index('timestamp', inplace=True)

        # Plotting
        plt.figure(figsize=(12, 6))
        plt.plot(self.single_pair_data.index,
                 self.single_pair_data[self.symbol_one], label=self.symbol_one)
        plt.plot(self.single_pair_data.index,
                 self.single_pair_data[self.symbol_two], label=self.symbol_two)

        # Adding labels and title
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.title(
            f'Price Comparison of {self.symbol_one} and {self.symbol_two} Over Time')
        plt.legend()

        # Display the plot
        plt.show()
