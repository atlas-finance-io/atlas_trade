import pandas as pd
import ccxt
from statsmodels.regression.rolling import RollingOLS
from statsmodels.tsa.stattools import adfuller
import statsmodels.api as sm
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import coint


class StatArbBacktester():
    def __init__(self, exchange, symbol_one, symbol_two, lower_threshold, upper_threshold, exit_threshold, lookback_window, zscore_window, position_size, trading_days, trading_costs=-0.0005):
        self.exchange = exchange
        self.symbol_one = symbol_one
        self.symbol_two = symbol_two
        self.trading_costs = trading_costs
        self.trading_days = trading_days

        self.hedge_ratio = None
        self.data = self.fetch_prices()
        self.trading_periods_year = (self.data[self.symbol_one].count(
        ) / ((self.data.index[-1] - self.data.index[0]).days / 365.25))

        self.results = None
        self.entry_tracking = {
            symbol_one: {
                'units': 0,
                'price': 0,
            },
            symbol_two: {
                'units': 0,
                'price': 0
            },
            'portfolio_entry_value': 10000
        }

        # =================== Strategy Parameters ========================
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold
        self.exit_threshold = exit_threshold
        self.lookback_window = lookback_window
        self.zscore_window = zscore_window
        self.position_size = position_size

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
                    symbol_one, '1h', since=since_timestamp, limit=1000, params={'price': 'mark'})
                ohlcv_two = self.exchange.fetch_ohlcv(
                    symbol_two, '1h', since=since_timestamp, limit=1000, params={'price': 'mark'})

                # Create temporary dataframes to hold fetched data
                df_one_temp = pd.DataFrame(
                    ohlcv_one, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_two_temp = pd.DataFrame(
                    ohlcv_two, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Check if both dataframes have the same length
                if len(df_one_temp) != len(df_two_temp):
                    print(
                        f"Data length mismatch: {self.symbol_one} has {len(df_one_temp)} rows, {self.symbol_two} has {len(df_two_temp)} rows.")
                    return None

                # Merge dataframes
                df_temp = pd.merge(df_one_temp[['timestamp', 'close']], df_two_temp[[
                                   'timestamp', 'close']], on='timestamp', how='inner')
                df_temp.columns = ['timestamp',
                                   self.symbol_one, self.symbol_two]

                # Concatenate with the final dataframe
                df_prices = pd.concat([df_prices, df_temp])

                # Update the since_timestamp to the last timestamp fetched
                since_timestamp = df_prices['timestamp'].max(
                ) + (60 * 60 * 1000)  # Add one hour

            except Exception as e:
                print(f"Error in fetching prices: {e}")
                break

        # Calculate Hedge ratio over the whole dataset
        x = df_prices[self.symbol_one]
        y = df_prices[self.symbol_two]

        # model = sm.OLS(y, sm.add_constant(x)).fit()
        # hedge_ratio = model.params[1]
        # print(f"Current Hedge Ratio: {hedge_ratio}")
        # self.hedge_ratio = hedge_ratio

        # Remove duplicates and sort the dataframe
        df_prices.drop_duplicates(
            subset='timestamp', keep='first', inplace=True)
        df_prices.sort_values(by='timestamp', inplace=True)
        # Convert 'timestamp' to datetime
        df_prices['date'] = pd.to_datetime(df_prices['timestamp'], unit='ms')

        df_prices.set_index('date', inplace=True)

        # Ensure there are no duplicates
        df_prices.drop_duplicates(inplace=True)

        return df_prices

    def cointegration_check(self):
        x = self.data[self.symbol_one]
        y = self.data[self.symbol_two]

        if len(x) != len(y):
            print(f"Mismatch for Price Lengths")

        result = coint(x, y)
        score = result[0]
        pvalue = result[1]

        print("P Value: ", pvalue)

        if pvalue < 0.05:
            print("Potential Cointegration")
        else:
            print("Not Cointegrated")

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

    def generate_signals(self):
        try:
            if self.data is None:
                print("Error with fetching market data")
                return

            # Generate z score
            df = self.data.copy()
            df['trading_signal'] = 0
            df['symbol_one_position'] = 0
            df['symbol_two_position'] = 0
            df['portfolio_value'] = 10000

            df["hedge_ratio"] = self.rolling_hedge_ratio(df[self.symbol_two], df[self.symbol_one], self.lookback_window)

            df['calculated_spread'] = df[self.symbol_two] - \
                df['hedge_ratio'] * df[self.symbol_one]

            df['rolling_mean_spread'] = df['calculated_spread'].rolling(
                window=self.zscore_window).mean()
            df['rolling_std_spread'] = df['calculated_spread'].rolling(
                window=self.zscore_window).std()
            df['z_score'] = (df['calculated_spread'] -
                             df['rolling_mean_spread']) / df['rolling_std_spread']

            df = df.reset_index(drop=True)

            # Generate signals based on z score thresholds
            for i in range(1, len(df)):
                # If z-score crosses below lower threshold, go long on symbol_two (dependent)
                if df.loc[i, 'z_score'] < self.lower_threshold and df.loc[i-1, 'z_score'] >= self.lower_threshold:
                    df.loc[i, 'trading_signal'] = 1

                # If z-score crosses above upper threshold, go short on symbol_two (dependent)
                elif df.loc[i, 'z_score'] > self.upper_threshold and df.loc[i-1, 'z_score'] <= self.upper_threshold:
                    df.loc[i, 'trading_signal'] = -1

                # If z-score crosses the zero line from above or below, go neutral
                elif (df.loc[i, 'z_score'] < self.exit_threshold and df.loc[i-1, 'z_score'] > self.exit_threshold) or \
                        (df.loc[i, 'z_score'] > -self.exit_threshold and df.loc[i-1, 'z_score'] < -self.exit_threshold):
                    df.loc[i, 'trading_signal'] = 0

                # If z-score crosses the zero line from above or below, close positions
                elif (df.loc[i, 'z_score'] < 0 and df.loc[i-1, 'z_score'] > 0) or \
                        (df.loc[i, 'z_score'] > 0 and df.loc[i-1, 'z_score'] < 0):
                    df.loc[i, 'trading_signal'] = 0

                # Else, maintain the previous signal
                else:
                    df.loc[i, 'trading_signal'] = df.loc[i-1, 'trading_signal']

            self.data = df

        except Exception as e:
            print(f"Error in generate signals: {e}")

    def run_backtest(self):

        df = self.data.copy()
        current_position = 0

        for index, row in df.iterrows():

            # Skip the first row
            if index == 0:
                continue

            trading_signal = row['trading_signal']
            hedge_ratio = row['hedge_ratio']

            symbol_one_price = row[self.symbol_one]
            symbol_two_price = row[self.symbol_two]

            symbol_two_qty = position_size
            symbol_one_qty = symbol_two_qty * hedge_ratio

            # When we stay neutral
            if current_position == 0 and trading_signal == 0:

                # Maintaining Parameters from previous row
                df.at[index, 'symbol_one_position'] = df.at[index -
                                                            1, 'symbol_one_position']
                df.at[index, 'symbol_two_position'] = df.at[index -
                                                            1, 'symbol_two_position']
                df.at[index, 'portfolio_value'] = df.at[index -
                                                        1, 'portfolio_value']

            # Buy Symbol One, Short Symbol Two Condition (LONG SPREAD)
            if current_position == 0 and trading_signal == 1:

                df.at[index, 'symbol_two_position'] = symbol_two_qty
                df.at[index, 'symbol_one_position'] = -symbol_one_qty

                # portfolio value shouldnt change
                df.at[index, 'portfolio_value'] = df.at[index -
                                                        1, 'portfolio_value']

                # Update entry tracking
                self.entry_tracking[self.symbol_one]['units'] = symbol_one_qty
                self.entry_tracking[self.symbol_one]['price'] = symbol_one_price

                self.entry_tracking[self.symbol_two]['units'] = symbol_two_qty
                self.entry_tracking[self.symbol_two]['price'] = symbol_two_price

                # Update portfolio entry value, we entered a position, record our entry portfolio value
                self.entry_tracking['portfolio_entry_value'] = df.at[index -
                                                                     1, 'portfolio_value']

                # update current position
                current_position = 1

            # Short Symbol One, Buy Symbol Two Condition (SHORT SPREAD)
            elif current_position == 0 and trading_signal == -1:

                df.at[index, 'symbol_one_position'] = symbol_one_qty
                df.at[index, 'symbol_two_position'] = -symbol_two_qty

                # portfolio value shouldnt change
                df.at[index, 'portfolio_value'] = df.at[index -
                                                        1, 'portfolio_value']

                # Update entry tracking
                self.entry_tracking[self.symbol_one]['units'] = symbol_one_qty
                self.entry_tracking[self.symbol_one]['price'] = symbol_one_price

                self.entry_tracking[self.symbol_two]['units'] = symbol_two_qty
                self.entry_tracking[self.symbol_two]['price'] = symbol_two_price

                # Update portfolio entry value, we entered a position, record our entry portfolio value
                self.entry_tracking['portfolio_entry_value'] = df.at[index -
                                                                     1, 'portfolio_value']

                # update current position
                current_position = -1

            # If we are maintaining a long or short spread position, logic should be the same
            elif (current_position == 1 and trading_signal == 1) or (current_position == -1 and trading_signal == -1):

                # Maintaining Parameters from previous row
                df.at[index, 'symbol_one_position'] = df.at[index -
                                                            1, 'symbol_one_position']
                df.at[index, 'symbol_two_position'] = df.at[index -
                                                            1, 'symbol_two_position']

                # Updating portfolio value with current prices
                portfolio_entry_value = self.entry_tracking['portfolio_entry_value']

                # Long Symbol Two and Short hedge ratio * symbol one
                if trading_signal == 1:

                    # Long case. Gains would be current - entry
                    symbol_two_entry_value = self.entry_tracking[self.symbol_two]['units'] * \
                        self.entry_tracking[self.symbol_two]['price']
                    symbol_two_current_value = self.entry_tracking[
                        self.symbol_two]['units'] * symbol_two_price
                    symbol_two_gain = symbol_two_current_value - symbol_two_entry_value

                    # Short case Gains would be entry - current
                    symbol_one_entry_value = self.entry_tracking[self.symbol_one]['units'] * \
                        self.entry_tracking[self.symbol_one]['price']
                    symbol_one_current_value = self.entry_tracking[
                        self.symbol_one]['units'] * symbol_one_price
                    symbol_one_gain = symbol_one_entry_value - symbol_one_current_value

                    total_gain = symbol_one_gain + symbol_two_gain
                    df.at[index, 'portfolio_value'] = portfolio_entry_value + total_gain

                # Shorting Symbol Two and Longing hedge ratio * symbol One
                if trading_signal == -1:

                    # Short case Gains would be entry - current
                    symbol_two_entry_value = self.entry_tracking[self.symbol_two]['units'] * \
                        self.entry_tracking[self.symbol_two]['price']
                    symbol_two_current_value = self.entry_tracking[
                        self.symbol_two]['units'] * symbol_two_price
                    symbol_two_gain = symbol_two_entry_value - symbol_two_current_value

                    # Long Case Gains would be current - Entry
                    symbol_one_entry_value = self.entry_tracking[self.symbol_one]['units'] * \
                        self.entry_tracking[self.symbol_one]['price']
                    symbol_one_current_value = self.entry_tracking[
                        self.symbol_one]['units'] * symbol_one_price
                    symbol_one_gain = symbol_one_current_value - symbol_one_entry_value

                    total_gain = symbol_one_gain + symbol_two_gain
                    df.at[index, 'portfolio_value'] = portfolio_entry_value + total_gain

            # Go Neutral
            elif current_position != 0 and trading_signal == 0:

                portfolio_entry_value = self.entry_tracking['portfolio_entry_value']

                # Update Portfolio Value once we've exited positions
                if current_position == 1:

                    # Long case. Gains would be current - entry
                    symbol_two_entry_value = self.entry_tracking[self.symbol_two]['units'] * \
                        self.entry_tracking[self.symbol_two]['price']
                    symbol_two_current_value = self.entry_tracking[
                        self.symbol_two]['units'] * symbol_two_price
                    symbol_two_gain = symbol_two_current_value - symbol_two_entry_value

                    # Short case Gains would be entry - current
                    symbol_one_entry_value = self.entry_tracking[self.symbol_one]['units'] * \
                        self.entry_tracking[self.symbol_one]['price']
                    symbol_one_current_value = self.entry_tracking[
                        self.symbol_one]['units'] * symbol_one_price
                    symbol_one_gain = symbol_one_entry_value - symbol_one_current_value

                    total_gain = symbol_one_gain + symbol_two_gain
                    df.at[index, 'portfolio_value'] = portfolio_entry_value + total_gain

                if current_position == -1:

                    # Short case Gains would be entry - current
                    symbol_two_entry_value = self.entry_tracking[self.symbol_two]['units'] * \
                        self.entry_tracking[self.symbol_two]['price']
                    symbol_two_current_value = self.entry_tracking[
                        self.symbol_two]['units'] * symbol_two_price
                    symbol_two_gain = symbol_two_entry_value - symbol_two_current_value

                    # Long Case Gains would be current - Entry
                    symbol_one_entry_value = self.entry_tracking[self.symbol_one]['units'] * \
                        self.entry_tracking[self.symbol_one]['price']
                    symbol_one_current_value = self.entry_tracking[
                        self.symbol_one]['units'] * symbol_one_price
                    symbol_one_gain = symbol_one_current_value - symbol_one_entry_value

                    total_gain = symbol_one_gain + symbol_two_gain
                    df.at[index, 'portfolio_value'] = portfolio_entry_value + total_gain

                # Update positions, since at this point we have exited
                df.at[index, 'symbol_one_position'] = 0
                df.at[index, 'symbol_two_position'] = 0

                # update current position
                current_position = 0

        df['returns'] = np.log(df['portfolio_value'] /
                               df['portfolio_value'].shift(1))
        df["cumulative_returns"] = df["returns"].cumsum().apply(np.exp)
        self.results = df

    def calculate_multiple(self, series):
        return np.exp(series.sum())

    def calculate_cagr(self, series):
        print("DAYS: ", series.index[-1] - series.index[0])
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

    def print_performance(self):
        ''' Calculates and prints various Performance Metrics.
        '''

        data = self.results.copy()
        data['date'] = pd.to_datetime(data['timestamp'], unit='ms')
        data.set_index('date', inplace=True)

        strategy_multiple = round(self.calculate_multiple(data.returns), 6)
        cagr = round(self.calculate_cagr(data.returns), 6)
        ann_mean = round(self.calculate_annualized_mean(data.returns), 6)
        ann_std = round(self.calculate_annualized_std(data.returns), 6)
        sharpe = round(self.calculate_sharpe(data.returns), 6)

        print(100 * "=")
        print("Statistical Arbitrage | Symbol One = {} | Symbol Two = {}".format(
            self.symbol_one, self.symbol_two))
        print(100 * "-")
        print("PERFORMANCE MEASURES:")
        print("\n")
        print("Multiple (Strategy):         {}".format(strategy_multiple))
        print(38 * "-")
        print("\n")
        print("CAGR:                        {}".format(cagr))
        print("Annualized Mean:             {}".format(ann_mean))
        print("Annualized Std:              {}".format(ann_std))
        print("Sharpe Ratio:                {}".format(sharpe))

        print(100 * "=")

        data = data.reset_index(drop=True)
        data.to_csv('results.csv', index=True)

    def plot_results(self):
        if self.data is None:
            print("Run backtest first")
        else:
            title = "Symbol One: {} | Symbol Two: = {}".format(
                self.symbol_one, self.self.symbol_two)
            self.data[["cumulative_returns"]].plot(
                title=title, figsize=(12, 8))


exchange = ccxt.binance()

symbol_one = "ATOMUSDT"
symbol_two = "AXSUSDT"
position_size = 700
trading_days = 120


# =================== Strategy Parameters ========================
lower_threshold = -2
upper_threshold = 2
exit_threshold = 0.3
lookback_window = 500
zscore_window = 30


binance_pairs_trader = StatArbBacktester(exchange, symbol_one, symbol_two,
                                         lower_threshold, upper_threshold, exit_threshold, lookback_window, zscore_window, position_size, trading_days)

binance_pairs_trader.cointegration_check()
binance_pairs_trader.generate_signals()

binance_pairs_trader.run_backtest()

binance_pairs_trader.print_performance()
