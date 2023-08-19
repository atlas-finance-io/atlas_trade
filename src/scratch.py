
from ib_insync import *
import pandas as pd
import time
# Import the Historicals class from ib_historicals.py
from utils.ib_utils.ib_historicals import IBHistoricals
from utils.technical_indicators import average_true_range, macd, relative_strength_index

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

tesla_contract = Stock('TSLA', 'SMART', 'USD')

historicals = IBHistoricals(ib, tesla_contract, duration='1 Y')

df = historicals.fetch_historicals()

print(df)

df_atr = average_true_range(df)

df_atr.to_csv(tesla_contract.symbol + '_ATR.csv', index=False)

ib.disconnect()
