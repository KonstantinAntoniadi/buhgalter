import asyncio

from bank_clients.neolegoff_bank import AioNeolegoff
from bank_clients.yandex.yandex_client import YandexClient
from bank_clients.tnikoff_invest.tinkoff_invest_client import TBankInvestClient
from balance_updaters.tinkoff_invest_updater import TinkoffInvestBalanceUpdater
from balance_updaters.tinkoff_bank_updater import TinkoffBankBalanceUpdater
from balance_updaters.yandex_bank_updater import YandexBankBalanceUpdater
from balance_updaters.base_updater import BaseUpdater
from modules.pg_module import PgModule
from modules.telegram import TgBot
from bank_clients.neolegoff_bank.models.db_models import *
from modules.vault_client import *
from creds.login_data import *


async def update_money_pipline(client: BaseUpdater, tg_bot):
    try:
        await client.authorize()
        await client.update_balance()
        await client.update_operations()
        message = f"{client.title} balance was updated successfully"
        print(message)
        await tg_bot.seng_message(message)
    except Exception as e:
        message = f"Erorr while update {client.title} balance: {e}"
        print(message)
        await tg_bot.seng_message(message)


async def main():
    vault_client = VaultClient(VAULT_URL, VAULT_ROOT_TOKEN)
    tg_bot = TgBot(vault_client.get_tg_token(), vault_client.get_chat_id())

    tinkoff_client = AioNeolegoff(app_name="main40:whitepfelka",
                                  base64_secret_key=vault_client.get_tinkoff_base64_secret_key())
    tinkoff_invest_client = TBankInvestClient(
        auth_token=vault_client.get_tinkoff_invest_token())

    yandex_client = YandexClient(
        tg_client=tg_bot, base64_key=vault_client.get_yandex_base64_secret_key())

    pg_module = PgModule(
        db_user=vault_client.get_db_user(),
        db_password=vault_client.get_db_password(),
        db_host=vault_client.get_db_host(),
        db_port=vault_client.get_db_port(),
        db_name=vault_client.get_db_name(),
    )

    tinkoff_bank_updater = TinkoffBankBalanceUpdater(
        client=tinkoff_client,
        pg_module=pg_module,
        login_phone=vault_client.get_tinkoff_phone(),
        password=vault_client.get_tinkoff_password(),
        card=vault_client.get_tinkoff_card(),
        owner_phone=vault_client.get_owner_phone_1(),
        owner_name=vault_client.get_owner_name_with_initial(),
    )

    yandex_updater = YandexBankBalanceUpdater(
        client=yandex_client, pg_module=pg_module, login=vault_client.get_yandex_login(),
        owner_phone_formatted_1=vault_client.get_owner_phone_formatted_1())
    tinkoff_invest_updater = TinkoffInvestBalanceUpdater(
        tinkoff_invest_client, pg_module)
    updaters = [
        yandex_updater,
        tinkoff_invest_updater,
        tinkoff_bank_updater
    ]
    tasks = [update_money_pipline(updater, tg_bot) for updater in updaters]
    await asyncio.gather(*tasks)


asyncio.run(main())
