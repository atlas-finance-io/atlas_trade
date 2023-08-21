from ib_insync import *
import json
import pandas as pd


class IBPortfolio:
    def __init__(self, ib):
        self.ib = ib

    def managed_accounts(self):
        managed_accounts = self.ib.managedAccounts()
        print("Managed Accounts: ", managed_accounts)
        return managed_accounts

    def account_values(self, account=""):
        account_values = self.ib.accountValues(account)
        print("Account Values: ", account_values)
        return account_values

    def account_summary(self, account=""):
        account_summary = self.ib.accountSummary(account)
        print("Account Summary: ", json.dumps(account_summary, indent=4))
        return account_summary

    def positions(self, account=""):
        positions = self.ib.positions(account)
        positions_data = []
        for position in positions:
            positions_data.append({
                "Account": position.account,
                "Symbol": position.contract.symbol,
                "SecType": position.contract.secType,
                "Currency": position.contract.currency,
                "Position": position.position,
                "AvgCost": position.avgCost
            })

        print(pd.DataFrame(positions_data))
        return positions

    def profit_loss(self, account="", model_code=""):
        pnl = self.ib.pnl(account, model_code)
        print("Profit & Loss: ", json.dumps(pnl, indent=4))
        return pnl

    def all_trades(self):
        trades = self.ib.trades()
        print("All trades for this session:", trades)
        return trades

    def all_open_trades(self):
        trades = self.ib.openTrades()
        print("All open trades for this session:", trades)
        return trades

    def executions(self):
        executions = self.ib.execution()
        print("All executions for the session: ", executions)
        return executions
