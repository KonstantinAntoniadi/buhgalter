import asyncio

from balance_updaters.base_updater import *


class YandexBankBalanceUpdater(BaseUpdater):
    def __init__(self, client, pg_module, login, owner_phone_formatted_1):
        super().__init__("Yandex bank", client, pg_module)
        self.login = login
        self.owner_phone_formatted_1 = owner_phone_formatted_1

    async def authorize(self):
        await self.client.authorize(self.login)

    async def update_balance(self):
        yandex_products = await self.client.get_products()
        self.pg_module.upsert_yandex_accounts(yandex_products)

    async def update_operations(self):
        async def process_item(item):
            operation_info = await self.client.get_operation_info(id=item.id)
            return operation_info.data.bank_user.operation

        items = (await self.client.get_operations(size=40)).data.result.items
        tasks = [process_item(item) for item in items]
        operations = await asyncio.gather(*tasks)
        self.pg_module.add_yandex_operations(
            operations, self.owner_phone_formatted_1)
