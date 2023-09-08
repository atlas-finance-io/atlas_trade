import boto3
import csv
import os
from dotenv import load_dotenv
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Configure the AWS credentials and region
aws_access_key_id = "AKIAYBRRVOADM7WTEU4R"
aws_secret_access_key = "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"
region_name = 'us-east-1'

# Create a DynamoDB client
dynamodb = boto3.client('dynamodb', aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key, region_name=region_name)

# Define the query parameters
table_name = 'crypto-master-prod'
index_name = 'marketCapIndex'  # Your secondary index name
limit = 500


scan_params = {
    'TableName': table_name,
    # Only retrieve these attributes
    'ProjectionExpression': 'id, symbol, cryptoName, marketCap',
}

# Initialize variables
all_items = []

# Perform the scan in a loop to handle pagination
while True:
    response = dynamodb.scan(**scan_params)
    all_items.extend(response['Items'])

    # Check if there are more items to fetch
    if 'LastEvaluatedKey' in response:
        scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
    else:
        break

# Sort the items based on the 'marketCap' attribute if it exists
sorted_items = sorted(all_items, key=lambda x: float(
    x.get('marketCap', {'N': '0'})['N']), reverse=True)

# Get the top items
top_items = sorted_items[:limit]

# Save the items as a CSV file
csv_file = 'top_coins.csv'
with open(csv_file, 'w', newline='') as file:
    csv_writer = csv.writer(file)
    csv_writer.writerow(['id', 'symbol', 'cryptoName', 'marketCap'])

    for item in top_items:
        row = [item['id']['S'], item['symbol']['S'], item['cryptoName']
               ['S'], item.get('marketCap', {'N': '0'})['N']]
        csv_writer.writerow(row)

print(f'Saved the top {limit} items to {csv_file}')
