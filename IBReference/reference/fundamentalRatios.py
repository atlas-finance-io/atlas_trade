from ib_insync import *
import pandas as pd

# Connect to IB
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Define the contract
contract = Stock('AAPL', 'SMART', 'USD')

# Request market data
ticker = ib.reqMktData(contract, '258')
ib.sleep(2)

# Get fundamental data
fundamental_data = ticker.fundamentalRatios

# Create a list of dictionaries for DataFrame
data_list = []
for attr, value in fundamental_data.__dict__.items():
    data_list.append({'Metric': attr, 'Value': value})

# Create a DataFrame
df = pd.DataFrame(data_list)

# Adjust display options to print the entire DataFrame
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.expand_frame_repr', False)

# Print the DataFrame
print(df)

# Disconnect from IB
ib.disconnect()
