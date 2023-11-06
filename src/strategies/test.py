import ccxt
import pandas as pd
from datetime import datetime

import schedule
import time
pd.set_option('display.max_rows', None)

exchange = ccxt.binanceus({
    "apiKey": "48ec6d428ba946e5cb872151695dface9bbe82558174f2cf46b67b91e362394b",
    "secret": "1d20d89e04bd9268ef2ab7c14db137e9d6490869b7ec703de4b423a3cb14c417"
})

exchange.set_sandbox_mode(True)


def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', limit=100)
    df = pd.DataFrame(bars[:-1], columns=['timestamp',
                      'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')


schedule.every(10).seconds.do(run_bot)


while True:
    schedule.run_pending()
    time.sleep(1)
