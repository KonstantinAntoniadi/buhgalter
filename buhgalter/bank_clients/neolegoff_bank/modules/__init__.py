# isort: off

from bank_clients.neolegoff_bank.modules.core import AioNeolegoffCore
from bank_clients.neolegoff_bank.modules.auth import AioNeolegoffAuth
from bank_clients.neolegoff_bank.modules.products import AioNeolegoffProducts
from bank_clients.neolegoff_bank.modules.operations import AioNeolegoffOperations

# isort: on


class AioNeolegoff:
    def __init__(self, base64_secret_key: str, app_name):
        self.core = AioNeolegoffCore(
            base64_secret_key=base64_secret_key, app_name=app_name)

        self.auth: AioNeolegoffAuth = AioNeolegoffAuth(self)
        self.products: AioNeolegoffProducts = AioNeolegoffProducts(self)
        self.operations: AioNeolegoffOperations = AioNeolegoffOperations(self)

    @property
    def is_login_required(self) -> bool:
        return self.core.tokens is None

    @property
    def is_refresh_tokens_required(self):
        return not self.core.tokens.is_access_token_alive
