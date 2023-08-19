from ib_insync import *


class IBScanner:
    def __init__(self, ib, instrument_type, location_code, scan_code, tags_dict):
        self.ib = ib
        self.instrument_type = instrument_type
        self.location_code = location_code
        self.scan_code = scan_code
        self.tags_dict = tags_dict

    def run_scan(self):
        sub = ScannerSubscription(
            instrument=self.instrument_type,
            locationCode=self.location_code,
            scanCode=self.scan_code)

        tag_values = [TagValue(tag, value)
                      for tag, value in self.tags_dict.items()]

        # the tagValues are given as the 3rd argument; the 2nd argument must always be an empty list
        scan_data = self.ib.reqScannerData(sub, [], tag_values)
        symbols = [sd.contractDetails.contract.symbol for sd in scan_data]
        return symbols


ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Example tags dictionary
tags_dict = {
    'changePercAbove': '20',
    'priceAbove': '5',
    'priceBelow': '50'
}


# Create an instance of IBScanner
scanner = IBScanner(
    ib,
    instrument_type='STK',
    location_code='STK.US.MAJOR',
    scan_code='TOP_PERC_GAIN',
    tags_dict=tags_dict
)

# Run the scanner
symbols = scanner.run_scan()

# Print the scanned symbols
print("Scanned Symbols:")
for symbol in symbols:
    print(symbol)

ib.disconnect()
