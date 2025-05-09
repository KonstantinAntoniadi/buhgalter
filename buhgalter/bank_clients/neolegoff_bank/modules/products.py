from bank_clients.neolegoff_bank.models.products.accounts import Accounts
from bank_clients.neolegoff_bank.modules._helpers import prepare_response
from bank_clients.neolegoff_bank.modules._module_parent import AioNeolegoffModuleParent


class AioNeolegoffProducts(AioNeolegoffModuleParent):
    @prepare_response()
    async def get_products(self) -> Accounts:
        response = await self.core.session.post(
            url=f"https://api.tinkoff.ru/v1/accounts_flat?",
            params=self.core.app_data_payload,
        )

        return response
