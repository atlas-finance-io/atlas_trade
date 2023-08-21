from ibapi.order import Order
from ibapi.contract import Contract
from ib_insync import *

"""
Current state vs request
Doing a request involves network traffic going up and down and can take considerable time. 
The current state on the other hand is always immediately available. So it is preferable to 
use the current state methods over requests. For example, use ib.openOrders() in preference 
over ib.reqOpenOrders(), or ib.positions() over ib.reqPositions(), etc:
"""


class IBOrder:
    def __init__(self, ib):
        self.ib = ib
        self.order = Order()

    def limit_order(self, direction, quantity, lmt_price):
        self.order.action = direction
        self.order.orderType = "LMT"
        self.order.totalQuantity = quantity
        self.order.lmtPrice = lmt_price

    def market_order(self, direction, quantity):
        self.order.action = direction
        self.order.orderType = "MKT"
        self.order.totalQuantity = quantity

    def stop_order(self, direction, quantity, st_price):
        self.order.action = direction
        self.order.orderType = "STP"
        self.order.totalQuantity = quantity
        self.order.auxPrice = st_price

    def trail_stop_order(self, direction, quantity, st_price, tr_step=1):
        self.order.action = direction
        self.order.orderType = "TRAIL"
        self.order.totalQuantity = quantity
        self.order.auxPrice = tr_step
        self.order.trailStopPrice = st_price

    def bracket_order(self, action, quantity, limit_price, take_profit_price, stop_loss_price):
        bracket = self.ib.bracketOrder(
            action, quantity, limit_price, take_profit_price, stop_loss_price)
        return bracket

    def place_order(self):
        """
        placeOrder is not blocking and will not wait on what happens with the order. 
        To make the order placement blocking, that is to wait until the order is either 
        filled or canceled, consider the following:
        """
        trade = self.ib.placeOrder(self.contract, self.order)
        while not trade.isDone():
            self.ib.waitOnUpdate()

    def what_if_order(self):
        self.ib.whatIfOrder(self.contract, self.order)


# ib = IB()
# ib.connect('127.0.0.1', 7497, clientId=1)

# contract = Contract()
# contract.symbol = "SPY"
# contract.secType = "STK"
# contract.currency = "USD"
# contract.exchange = "SMART"
# contract.primaryExchange = "ARCA"

# order = IBOrder(ib, contract)
# order.market_order("BUY", 100)
# order.place_order()
