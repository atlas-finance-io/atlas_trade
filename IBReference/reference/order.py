from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=13)

contract = Forex('EURUSD')
ib.qualifyContracts(contract)

# Action, Quantity, Limit
order = LimitOrder('SELL', 20000, 1.11)

# placeOrder will place the order order and return a Trade object right away (non-blocking):
trade = ib.placeOrder(contract, order)

# trade contains the order and everything related to it, such as order status, fills and a log.
# It will be live updated with every status change or fill of the order.

# trade will also available from ib.trades():
assert trade in ib.trades()

assert order in ib.orders()


limitOrder = LimitOrder('BUY', 20000, 0.05)
limitTrade = ib.placeOrder(contract, limitOrder)

assert limitTrade in ib.openTrades()

# Lets modify the limit price and submit
limitOrder.lmtPrice = 0.10

ib.placeOrder(contract, limitOrder)

# and we can cancel it
ib.cancelOrder(limitOrder)

# placeOrder is not blocking and will not wait on what happens with the order. To make the order placement blocking,
# that is to wait until the order is either filled or canceled, consider the following:

order = MarketOrder('BUY', 100)

trade = ib.placeOrder(contract, order)
while not trade.isDone():
    ib.waitOnUpdate()

# We can find our positions with:
ib.positions()

# Whats the total of commisions paid today?
sum(fill.commissionReport.commission for fill in ib.fills())

# whatIfOrder can be used to see the commission and the margin impact of an order without actually sending the order:
order = MarketOrder('SELL', 20000)
ib.whatIfOrder(contract, order)

ib.disconnect()
