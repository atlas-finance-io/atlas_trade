from ib_insync import *
import pandas as pd
import time


from src.utils.ib_utils.ib_scan import IBScanner
from src.utils.ib_utils.ib_historicals import IBHistoricals
from src.utils.ib_utils.ib_portfolio import IBPortfolio
from src.utils.ib_utils.ib_order import IBOrder
from src.strategies.technical.technical_indicators import *


class FundamentallySoundLosers:
    def __init__(self, ib):
        self.ib = ib
        self.portfolio = IBPortfolio(ib)

        self.data = {}
        self.position_df = pd.DataFrame(columns=['Account', 'Symbol', 'SecType',
                                                 'Currency', 'Position', 'Avg cost'])
        self.order_df = pd.DataFrame(columns=['PermId', 'ClientId', 'OrderId',
                                              'Account', 'Symbol', 'SecType',
                                              'Exchange', 'Action', 'OrderType',
                                              'TotalQty', 'CashQty', 'LmtPrice',
                                              'AuxPrice', 'Status'])

    def historical_data(self, reqId, bar):
        if reqId not in self.data:
            self.data[reqId] = [{"date": bar.date, "open": bar.open, "high": bar.high,
                                 "low": bar.low, "close": bar.close, "volume": bar.volume}]
        else:
            self.data[reqId].append({"date": bar.date, "open": bar.open, "high": bar.high,
                                     "low": bar.low, "close": bar.close, "volume": bar.volume})

    def get_positions(self):
        positions = self.portfolio.positions()
        self.positions = positions


ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
time.sleep(2)


# Grab Biggest Losers of the day that are fundamentally sound
scanner = IBScanner(
    ib,
    instrument_type='STK',
    location_code='STK.US.MAJOR',
    scan_code='TOP_PERC_LOSE',
)


biggest_losers = scanner.run_blocking_scan()
print(biggest_losers)


app = FundamentallySoundLosers(ib)


def main():
    # Initialize what data we need to keep track of while the strategy is running
    # Our price data and technical indicators dataframe, position dataframe and order dataframe
    app.data = {}
    app.position_df = pd.DataFrame(columns=['Account', 'Symbol', 'SecType',
                                            'Currency', 'Position', 'Avg cost'])
    app.order_df = pd.DataFrame(columns=['PermId', 'ClientId', 'OrderId',
                                         'Account', 'Symbol', 'SecType',
                                         'Exchange', 'Action', 'OrderType',
                                         'TotalQty', 'CashQty', 'LmtPrice',
                                         'AuxPrice', 'Status'])
    app.get_positions()

    position_df = app.position_df.drop_duplicates(
        inplace=True, ignore_index=True)

    for symbol in biggest_losers:
        print('Starting passthrough for: ', symbol)

        # Check if we already have a position
        if symbol in position_df['Symbol'].values:
            continue

        if (fundamentally_sound(symbol)):
            contract = Stock(symbol, 'SMART', 'USD')
            ib.bracketOrder('BUY')


# extract and store historical data in dataframe repetitively
starttime = time.time()
timeout = time.time() + 60*60*6
while time.time() <= timeout:
    main()
    time.sleep(300 - ((time.time() - starttime) % 300.0))


# ib.disconnect()
