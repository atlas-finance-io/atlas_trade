import requests

# -----------------------------------------------------------------------------
# Sharadar Equities Bundle Client
#
# This is to interact with the sharadar equities bundle from nasdaq
#
# List of Tables:
# TICKERS: Metadata on companies ("table", "permaticker", "ticker", "name", "exchange", "isdelisted", "category", "cusips", "siccode", "sicsector", "sicindustry", "famasector", "famaindustry", "sector", "industry", "scalemarketcap", "scalerevenue", "relatedtickers", "currency", "location", "lastupdated", "firstadded", "firstpricedate", "lastpricedate", "firstquarter", "lastquarter", "secfilings", "companysite")
# SF1: Fundamentals ("ticker", "dimension", "calendardate", "datekey", "reportperiod", "lastupdated", "accoci", "assets", "assetsavg", "assetsc", "assetsnc", "assetturnover", "bvps", "capex", "cashneq", "cashnequsd", "cor", "consolinc", "currentratio", "de", "debt", "debtc", "debtnc", "debtusd", "deferredrev", "depamor", "deposits", "divyield", "dps", "ebit", "ebitda", "ebitdamargin", "ebitdausd", "ebitusd", "ebt", "eps", "epsdil", "epsusd", "equity", "equityavg", "equityusd", "ev", "evebit", "evebitda", "fcf", "fcfps", "fxusd", "gp", "grossmargin", "intangibles", "intexp", "invcap", "invcapavg", "inventory", "investments", "investmentsc", "investmentsnc", "liabilities", "liabilitiesc", "liabilitiesnc", "marketcap", "ncf", "ncfbus", "ncfcommon", "ncfdebt", "ncfdiv", "ncff", "ncfi", "ncfinv", "ncfo", "ncfx", "netinc", "netinccmn", "netinccmnusd", "netincdis", "netincnci", "netmargin", "opex", "opinc", "payables", "payoutratio", "pb", "pe", "pe1", "ppnenet", "prefdivis", "price", "ps", "ps1", "receivables", "retearn", "revenue", "revenueusd", "rnd", "roa", "roe", "roic", "ros", "sbcomp", "sgna", "sharefactor", "sharesbas", "shareswa", "shareswadil", "sps", "tangibles", "taxassets", "taxexp", "taxliabilities", "tbvps", "workingcapital")
# SF2: Insiders ("ticker", "filingdate", "formtype", "issuername", "ownername", "officertitle", "isdirector", "isofficer", "istenpercentowner", "transactiondate", "securityadcode", "transactioncode", "sharesownedbeforetransaction", "transactionshares", "sharesownedfollowingtransaction", "transactionpricepershare", "transactionvalue", "securitytitle", "directorindirect", "natureofownership", "dateexercisable", "priceexercisable", "expirationdate", "rownum")
# SF3: Institutional Investors Detailed  ("ticker", "investorname", "securitytype", "calendardate", "value", "units", "price")
# SF3A: Institutional Aggregated by ticker & Quarter ("calendardate", "ticker", "name", "shrholders", "cllholders", "putholders", "wntholders", "dbtholders", "prfholders", "fndholders", "undholders", "shrunits", "cllunits", "putunits", "wntunits", "dbtunits", "prfunits", "fndunits", "undunits", "shrvalue", "cllvalue", "putvalue", "wntvalue", "dbtvalue", "prfvalue", "fndvalue", "undvalue", "totalvalue", "percentoftotal")
# SF3B: Institutional Aggregated by investor & Quarter ("calendardate", "investorname", "shrholdings", "cllholdings", "putholdings", "wntholdings", "dbtholdings", "prfholdings", "fndholdings", "undholdings", "shrunits", "cllunits", "putunits", "wntunits", "dbtunits", "prfunits", "fndunits", "undunits", "shrvalue", "cllvalue", "putvalue", "wntvalue", "dbtvalue", "prfvalue", "fndvalue", "undvalue", "totalvalue", "percentoftotal")
# SEP: Equity Prices ("ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj", "lastupdated")
# DAILY: Daily Metrics ("ticker", "date", "lastupdated", "ev", "evebit", "evebitda", "marketcap", "pb", "pe", "ps")
# METRICS: More daily Metrics ("ticker", "date", "lastupdated", "beta1y", "beta5y", "dividendyieldforward", "dividendyieldtrailing", "high52w", "high5y", "low52w", "low5y", "ma200d", "ma200w", "ma50d", "ma50w", "price", "return1y", "return5y", "returnytd", "volume", "volumeavg1m", "volumeavg3m")
#
#
# -----------------------------------------------------------------------------


class SharadarClient:
    def __init__(self, api_key='zxLNKQydu_qNXQ2tZ7vz'):
        self.base_url = "https://data.nasdaq.com/api/v3/datatables/SHARADAR/"
        self.api_key = api_key

    def fetch_fundamental_data(self, table: str, tickers: str, columns: str):

        url = f"{self.base_url}{table}?ticker={tickers}&api_key={self.api_key}&qopts.columns={columns}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if "datatable" in data and "data" in data["datatable"]:
                return data["datatable"]["data"]
            else:
                print("Data not found in the response.")
                return None
        else:
            print("API request failed with status code:", response.status_code)
            return None
