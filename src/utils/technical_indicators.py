import numpy as np
import pandas as pd


def average_true_range(DF, n=14):
    df = DF.copy()
    df['H-L'] = abs(df['high']-df['low'])
    df['H-PC'] = abs(df['high']-df['close'].shift(1))
    df['L-PC'] = abs(df['low']-df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].ewm(com=n, min_periods=n).mean()
    return df


def macd(DF, a=12, b=26, c=9):
    df = DF.copy()
    df["ma_fast"] = df["close"].ewm(span=a, min_periods=a).mean()
    df["ma_slow"] = df["close"].ewm(span=b, min_periods=b).mean()
    df["macd"] = df["ma_fast"]-df["ma_slow"]
    df["signal"] = df["macd"].ewm(span=c, min_periods=c).mean()
    return df


def relative_strength_index(df, window=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    df['rsi'] = rsi
    return df


def average_directional_index(df, period=14):
    # Calculate +DM and -DM
    df['high_lag'] = df['high'].shift(1)
    df['low_lag'] = df['low'].shift(1)
    df['+dm'] = df.apply(lambda row: row['high'] - row['high_lag'] if row['high'] -
                         row['high_lag'] > row['low_lag'] - row['low'] else 0, axis=1)
    df['-dm'] = df.apply(lambda row: row['low_lag'] - row['low'] if row['low_lag'] -
                         row['low'] > row['high'] - row['high_lag'] else 0, axis=1)

    # Calculate True Range (TR)
    df['high_low'] = df['high'] - df['low']
    df['high_prevclose'] = abs(df['high'] - df['close'].shift(1))
    df['low_prevclose'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['high_low', 'high_prevclose', 'low_prevclose']].max(axis=1)

    # Calculate Smoothed +DM and -DM using EMA
    df['smoothed_+dm'] = df['+dm'].ewm(span=period, min_periods=period).mean()
    df['smoothed_-dm'] = df['-dm'].ewm(span=period, min_periods=period).mean()

    # Calculate Directional Index (DX)
    df['+di'] = 100 * (df['smoothed_+dm'] / df['tr'])
    df['-di'] = 100 * (df['smoothed_-dm'] / df['tr'])
    df['dx'] = 100 * (abs(df['+di'] - df['-di']) / (df['+di'] + df['-di']))

    # Calculate ADX using EMA of DX
    df['adx'] = df['dx'].ewm(span=period, min_periods=period).mean()

    df.drop(['high_lag', 'low_lag', '+dm', '-dm', 'high_low', 'high_prevclose',
            'low_prevclose', 'tr', 'smoothed_+dm', 'smoothed_-dm'], axis=1, inplace=True)

    return df


def stochastic_oscillator(df, n=14):
    high = df['high']
    low = df['low']
    close = df['close']

    stochastic_k = 100 * (close - low.rolling(n).min()) / \
        (high.rolling(n).max() - low.rolling(n).min())
    # Using a simple moving average for %D
    stochastic_d = stochastic_k.rolling(3).mean()

    df['%K'] = stochastic_k
    df['%D'] = stochastic_d

    return df


def bollinger_bands(data, window=20, num_std=2):
    """
    Calculate Bollinger Bands for a given DataFrame.

    Parameters:
        data (pd.DataFrame): DataFrame containing 'close' prices.
        window (int): Rolling window size for moving average and standard deviation.
        num_std (int): Number of standard deviations for upper and lower bands.

    Returns:
        pd.DataFrame: Original DataFrame with Bollinger Bands columns.
    """
    df = data.copy()

    # Calculate rolling mean and standard deviation
    df['rolling_mean'] = df['close'].rolling(window=window).mean()
    df['rolling_std'] = df['close'].rolling(window=window).std()

    # Calculate Bollinger Bands
    df['upper_band'] = df['rolling_mean'] + (num_std * df['rolling_std'])
    df['lower_band'] = df['rolling_mean'] - (num_std * df['rolling_std'])

    return df
