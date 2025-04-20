from balance_updaters.base_updater import *


class TinkoffInvestBalanceUpdater(BaseUpdater):
    def __init__(self, client, pg_module):
        super().__init__("Tinkoff invest", client, pg_module)

    async def authorize(self):
        pass

    async def update_balance(self):
        portfolios = await self.client.get_portfolios()
        self.pg_module.upsert_tinkoff_invest_accounts(portfolios)

    async def update_operations(self):
        pass
