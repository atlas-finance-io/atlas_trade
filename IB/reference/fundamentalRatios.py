from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)


contract = Stock('AAPL', 'SMART', 'USD')
ticker = ib.reqMktData(contract, '258')
ib.sleep(2)
print(ticker.fundamentalRatios)
