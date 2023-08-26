import requests
import csv

# Define the API URL
api_url = "https://91j3dag4m9.execute-api.us-east-1.amazonaws.com/master/getCMCPriceHistory/1?startDate=2017-01-01"

# Make the API call
response = requests.get(api_url)
data = response.json()

# Extract price history
price_history = data.get("priceHistory", [])

# Write the data to a CSV file
csv_filename = "crypto_price_history.csv"
with open(csv_filename, mode="w", newline="") as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(
        ["Date", "Open", "High", "Low", "Close", "Volume", "Market Cap"])

    for entry in price_history:
        row = [entry["d"], entry["o"], entry["h"], entry["l"],
               entry["c"], entry["v"], entry["mcap"]]
        csv_writer.writerow(row)

print(f"CSV file '{csv_filename}' created successfully.")
