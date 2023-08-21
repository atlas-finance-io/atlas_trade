
Certainly! Here's the equivalent Python code for the given JavaScript functions using the urllib.parse module for URL manipulation:

python
Copy code
from urllib.parse import urlparse, urlencode, urlunparse

def NasdaqClient(message, user):
    url, search_params = generateURL[message['dataProvider']](message)

    for param, value in search_params.items():
        if value:
            url = urlunparse(urlparse(url)._replace(
                query=urlencode({**urlparse(url).query, param: value})))

    url = urlunparse(urlparse(url)._replace(
        query=urlencode({**urlparse(url).query, "api_key": "zxLNKQydu_qNXQ2tZ7vz"})))

    print("Generated Nasdaq URL: ", url)
    return {
        "url": url,
    }

def generateURL(message):
    table = message["table"]
    url_prefix = f"https://data.nasdaq.com/api/v3/datatables/SHARADAR/{table}"
    url = urlparse(f"{url_prefix}")
    params = {
        "ticker": configureMultiEntity(message["tickers"], message["companyGrouping"]),
        "dimension": message.get("dimensions", "MRY"),
        "qopts.columns": configureMultiIndicator(
            message["indicators"], message["figureGrouping"]),
    }
    return {
        "url": url,
        "searchParams": params,
    }