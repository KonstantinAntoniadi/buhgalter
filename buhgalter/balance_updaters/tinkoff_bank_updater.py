import pytz
from datetime import datetime, timedelta

from balance_updaters.base_updater import *


class TinkoffBankBalanceUpdater(BaseUpdater):
    def __init__(self, client, pg_module, login_phone, password, card, owner_phone, owner_name):
        super().__init__("Tinkoff bank", client, pg_module)
        self.login_phone = login_phone
        self.password = password
        self.card = card
        self.owner_phone = owner_phone
        self.owner_name = owner_name

    async def authorize(self):
        await self.client.auth.login(
            self.login_phone,
            self.password,
            self.card
        )

    async def update_balance(self):
        products = await self.client.products.get_products()
        self.pg_module.upsert_tinkoff_products(
            products.currents,
            products.credits,
            products.multi_deposits,
            products.savings)

    async def update_operations(self):
        operations = (
            await self.client.operations.operations(
                start=datetime.now(pytz.timezone("Europe/Moscow")) - timedelta(days=10),
                end=datetime.now(pytz.timezone("Europe/Moscow"))
                # start=datetime(2025, 1, 20, 0, 0, 0, 0, )
            )
        ).operations
        self.pg_module.add_tinkoff_operations(operations, self.owner_phone, self.owner_name)
