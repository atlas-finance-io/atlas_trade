import base64

encoded_string = "aHR0cHM6Ly90bnM0bHBnbXppaXlwbnh4emVsNXNzNW55dTBuZnRvbC5sYW1iZGEtdXJsLnVzLWVhc3QtMS5vbi5hd3MvcmFtcC1jaGFsbGVuZ2UtaW5zdHJ1Y3Rpb25zLw=="

# Decode the Base64 string
decoded_bytes = base64.b64decode(encoded_string)

# Convert bytes to a string
decoded_string = decoded_bytes.decode('utf-8')

# Print the decoded string
print(decoded_string)
