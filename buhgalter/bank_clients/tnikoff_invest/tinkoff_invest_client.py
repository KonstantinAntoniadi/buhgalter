from tinkoff.invest import Client


class TBankInvestClient:
    def __init__(self, auth_token):
        self.auth_token = auth_token

    async def get_portfolios(self):
        with Client(self.auth_token) as invest_client:
            invest_accounts = invest_client.users.get_accounts()
            portfolios = []
            for account in invest_accounts.accounts:
                portfolios.append(invest_client.operations.get_portfolio(
                    account_id=account.id
                ))

            return portfolios
