import hvac


class VaultClient():
    def __init__(self, url, token):
        self.client = hvac.Client(
            url=url,
            token=token
        )

    def _get_value(self, path, key):
        read_response = self.client.secrets.kv.v2.read_secret_version(
            path=path, mount_point='kv')
        return read_response['data']['data'][key]

    def _get_bank_value(self, key):
        return self._get_value('banks', key)

    def _get_base64_key(self, app) -> str:
        return self._get_value('base64', key=app)

    def get_yandex_login(self) -> str:
        return self._get_bank_value('yandex_login')

    def get_tinkoff_phone(self) -> str:
        return self._get_bank_value('tinkoff_phone')

    def get_tinkoff_password(self) -> str:
        return self._get_bank_value('tinkoff_password')

    def get_tinkoff_card(self) -> str:
        return self._get_bank_value('tinkoff_card')

    def get_tinkoff_invest_token(self) -> str:
        return self._get_bank_value('tinkoff_invest_token')

    def get_owner_phone_1(self) -> str:
        return self._get_bank_value('owner_phone_1')

    def get_owner_phone_formatted_1(self) -> str:
        return self._get_bank_value('owner_phone_formatted_1')

    def get_owner_name_with_initial(self) -> str:
        return self._get_bank_value('owner_name_with_initial')

    def _get_database_vallue(self, key) -> str:
        return self._get_value(path='database', key=key)

    def get_db_user(self) -> str:
        return self._get_database_vallue('db_user')

    def get_db_password(self) -> str:
        return self._get_database_vallue('db_password')

    def get_db_host(self) -> str:
        return self._get_database_vallue('db_host')

    def get_db_port(self) -> str:
        return self._get_database_vallue('db_port')

    def get_db_name(self) -> str:
        return self._get_database_vallue('db_name')

    def _get_tg_value(self, key) -> str:
        return self._get_value(path='tg', key=key)

    def get_tg_token(self) -> str:
        return self._get_tg_value('tg_bot_token')

    def get_chat_id(self) -> str:
        return self._get_tg_value('tg_chat_id')

    def get_yandex_base64_secret_key(self) -> str:
        return self._get_base64_key(app="yandex_bank")

    def get_tinkoff_base64_secret_key(self) -> str:
        return self._get_base64_key(app="tinkoff_bank")
