from ib_insync import *
import asyncio

# Connect to the Interactive Brokers Gateway/TWS
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Define the contract (e.g., Apple stock)
contract = Stock('AAPL', 'SMART', 'USD')

# Define the moving average parameters
fast_ma_period = 50
slow_ma_period = 200

# Initialize the strategy


class MovingAverageCrossoverStrategy:
    def __init__(self, contract, fast_period, slow_period):
        self.contract = contract
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.data = []

    def historicalData(self, bars, has_new_bar):
        self.data.append(bars[0].close)
        if len(self.data) >= self.slow_period:
            fast_ma = sum(self.data[-self.fast_period:]) / self.fast_period
            slow_ma = sum(self.data[-self.slow_period:]) / self.slow_period
            if fast_ma > slow_ma:
                self.buy_signal()
            elif fast_ma < slow_ma:
                self.sell_signal()

    def buy_signal(self):
        print("Buy signal triggered!")
        if not ib.positions():
            order = MarketOrder('BUY', 100)  # Change quantity as needed
            trade = ib.placeOrder(self.contract, order)
            print("Market buy order placed:", trade)

    def sell_signal(self):
        print("Sell signal triggered!")
        if ib.positions():
            order = MarketOrder('SELL', 100)  # Change quantity as needed
            trade = ib.placeOrder(self.contract, order)
            print("Market sell order placed:", trade)


strategy = MovingAverageCrossoverStrategy(
    contract, fast_ma_period, slow_ma_period)
ib.reqHistoricalData(contract, endDateTime='', durationStr='1 D',
                     barSizeSetting='1 min', whatToShow='TRADES', useRTH=True, formatDate=1, keepUpToDate=True)

ib.run()
