import datetime
from ib_insync import *
import pandas as pd
import time


class IBHistoricals:
    def __init__(self, ib, contract, end_date_time='', duration='10 D', bar_size='1 day', what_to_show='MIDPOINT', use_rth=True, format_date=1):
        self.ib = ib
        self.contract = contract
        self.end_date_time = end_date_time
        self.duration = duration
        self.bar_size = bar_size
        self.what_to_show = what_to_show
        self.use_rth = use_rth
        self.format_date = format_date

        self.bars_list = []

    def fetch_consecutive_historicals(self):
        while True:
            bars = self.ib.reqHistoricalData(
                self.contract,
                endDateTime=self.end_date_time,
                durationStr=self.duration,
                barSizeSetting=self.bar_size,
                whatToShow=self.what_to_show,
                useRTH=self.use_rth,
                formatDate=self.format_date)
            if not bars:
                break
            self.bars_list.append(bars)
            time.sleep(1)

    def fetch_historicals(self):
        bars_list = []
        historicals = self.ib.reqHistoricalData(
            self.contract,
            endDateTime=self.end_date_time,
            durationStr=self.duration,
            barSizeSetting=self.bar_size,
            whatToShow=self.what_to_show,
            useRTH=self.use_rth,
            formatDate=self.format_date)
        bars_list.append(historicals)
        reverse = [b for bars in reversed(bars_list) for b in bars]
        df = util.df(reverse)
        return df

    def save_csv(self, current_bars):
        current_bars.to_csv(self.contract.symbol + '.csv', index=False)


ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

tesla_contract = Stock('TSLA', 'SMART', 'USD')

historicals = IBHistoricals(ib, tesla_contract)

df = historicals.fetch_historicals()

historicals.save_csv(df)

ib.disconnect()
