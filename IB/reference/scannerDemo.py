import xml.etree.ElementTree as ET
import webbrowser
from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)


'''
To create a scanner, create a ScannerSubscription to submit to the reqScannerData method. 
For any scanner to work, at least these three fields must be filled: instrument (the what), 
locationCode (the where), and scanCode (the ranking).
'''

sub = ScannerSubscription(
    instrument='STK',
    locationCode='STK.US.MAJOR',
    scanCode='TOP_PERC_GAIN')

tagValues = [
    TagValue("changePercAbove", "20"),
    TagValue('priceAbove', 5),
    TagValue('priceBelow', 50)]

# the tagValues are given as 3rd argument; the 2nd argument must always be an empty list
# (IB has not documented the 2nd argument and it's not clear what it does)
scanData = ib.reqScannerData(sub, [], tagValues)

symbols = [sd.contractDetails.contract.symbol for sd in scanData]
print(symbols)

xml = ib.reqScannerParameters()

path = 'scanner_parameters.xml'
with open(path, 'w') as f:
    f.write(xml)

webbrowser.open(path)


# parse XML document
tree = ET.fromstring(xml)

scanCodes = [e.text for e in tree.findall('.//scanCode')]

print(len(scanCodes), 'scan codes, showing the ones starting with "TOP":')
print([sc for sc in scanCodes])
