from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# newsProviders = ib.reqNewsProviders()
# print(newsProviders)
# codes = '+'.join(np.code for np in newsProviders)

# amd = Stock('AMD', 'SMART', 'USD')
# ib.qualifyContracts(amd)
# headlines = ib.reqHistoricalNews(amd.conId, codes, '', '', 10)
# latest = headlines[0]
# print(latest)
# article = ib.reqNewsArticle(latest.providerCode, latest.articleId)
# print(article)

ib.reqNewsBulletins(True)
ib.sleep(5)
print(ib.newsBulletins())
