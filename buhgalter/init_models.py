from sqlalchemy import Engine, create_engine
from bank_clients.neolegoff_bank.models.db_models import *
from modules.vault_client import *
from creds.login_data import *


def main():
    vault_client = VaultClient(VAULT_URL, VAULT_ROOT_TOKEN)
    db_user = vault_client.get_db_user()
    db_password = vault_client.get_db_password()
    db_host = vault_client.get_db_host()
    db_port = vault_client.get_db_port()
    db_name = vault_client.get_db_name()
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine: Engine = create_engine(database_url)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(e)


main()
