from datetime import datetime
from decimal import Decimal
from typing import List

from bank_clients.neolegoff_bank.models.db_models import *

from sqlalchemy import (
    create_engine,
    func,
    exc,
    asc,
    desc,
    and_,
    update,
    select,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB, insert


TINKOFF_BANK_NAME = "Tinkoff"
YANDEX_BANK_NAME = "Yandex"

YANDEX_PRODUCT_TITLE_TO_ACCOUNT_TYPE = {
    "Баллы Плюса": AccountTypeEnum.BONUS,
    "Карта": AccountTypeEnum.CARD,
    "Сейвы": AccountTypeEnum.SAVING,
}

YANDEX_PRODUCT_TITLE_TO_ID = {
    "Баллы Плюса": "yandex-plus",
    "Карта": "yandex-card",
    "Сейвы": "yandex-saving",
}


class PgModule:
    def __init__(self,  db_user, db_password, db_host, db_port, db_name):
        self.user = db_user
        self.password = db_password
        self.host = db_host
        self.port = db_port
        self.db_name = db_name
        self.database_url = (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        )
        self.engine = create_engine(self.database_url)
        self.session_local = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.session = None

    def _open_session(self):
        self.session = self.session_local()

    def _close_session(self):
        if self.session:
            self.session.close()

    def add_record(self, record):
        try:
            self._open_session()
            self.session.add(record)
            self.session.commit()
        except exc.IntegrityError as e:
            self.session.rollback()
            # print(f"Error pg_module: {e}")
        except Exception as e:
            self.session.rollback()
            print(f"Error pg_module: {e}")
        finally:
            self._close_session()

    def change_account_status(
        self,
        account_ids: List[str],
        value: StatusEnum
    ):
        try:
            self._open_session()
            self.session.query(Account).filter(Account.id.in_(
                account_ids)).update({Account.status: value})
            self.session.commit()
        except Exception as e:
            print(f"Erorr while change_account_status: {e}")
        finally:
            self._close_session()

    def get_debit_operations(
        self,
        # start: datetime | None = None,
        # end: datetime | None = None,
        # period: timedelta | None = timedelta(days=30),
    ):
        operations: List[Operation] = []
        try:
            self._open_session()
            operations = (
                self.session.query(Operation)
                .filter(
                    and_(
                        Operation.type == "Debit",
                        Operation.is_between_owner_accounts == False,
                    )
                )
                .order_by(Operation.created_at)
                .all()
            )
        except Exception as e:
            print(f"Erorr while getting debit operations: {e}")
        finally:
            self._close_session()

        return operations

    def get_account_ids(self,
                        bank_name,
                        type: AccountTypeEnum
                        ):
        account_ids = []
        try:
            self._open_session()
            account_ids = (
                self.session.query(Account.id)
                .filter(and_(Account.bank_name == bank_name,
                             Account.type == type)).all()
            )
        except Exception as e:
            print(f"Erorr while getting accounts: {e}")
        finally:
            self._close_session()

        return account_ids

    def upsert_account(self,
                       account: Account):
        try:
            self._open_session()
            stmt = insert(Account).values(id=account.id,
                                          bank_name=account.bank_name,
                                          name=account.name,
                                          type=account.type,
                                          status=account.status,
                                          amount=account.amount,
                                          currency=account.currency,
                                          updated_at=account.updated_at,
                                          raw_data=account.raw_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={'amount': stmt.excluded.amount,
                      'updated_at': stmt.excluded.updated_at}
            )
            self.session.execute(stmt)
            self.session.commit()

        except Exception as e:
            print(f"Erorr while upsert accounts: {e}")
        finally:
            self._close_session()

    def _is_between_owner_accounts(self, operation: Operation, owner_phone, owner_name) -> bool:
        if operation.group not in ["TRANSFER", "INCOME"]:
            return False
        if operation.group == "TRANSFER":
            return operation.payment.fields_values.pointer == owner_phone
        if operation.group == "INCOME":
            return operation.sender_details == owner_name

    def add_tinkoff_operations(self, operations, owner_phone, owner_name):
        for operation in operations:
            if not operation.is_inner and operation.status == "OK":
                opeartion_db = Operation(
                    bank_operation_id=operation.id,
                    bank_name="Tinkoff",
                    status="OK",
                    type=operation.type.lower(),
                    group=operation.group,
                    value=operation.amount.value,
                    currency=operation.amount.currency.name,
                    brand_name=operation.brand.name if operation.brand else None,
                    category=operation.spending_category.name,
                    cashback=(
                        operation.loyalty_bonus_summary.amount
                        if operation.loyalty_bonus_summary
                        else None
                    ),
                    is_between_owner_accounts=self._is_between_owner_accounts(
                        operation, owner_phone, owner_name),
                    created_at=operation.created_at,
                    raw_data=operation.raw,
                )
                self.add_record(opeartion_db)

    def _is_yandex_operations_between_owner_accounts(self, operation, owner_phone) -> bool:
        return (owner_phone in [operation.sender_phone, operation.recipients_phone])

    def add_yandex_operations(self, operations, owner_phone):
        for operation in operations:
            money_amount = operation.amount.money.amount if operation.amount.money else Decimal(
                0)
            plus_amount = operation.amount.plus if operation.amount.plus else Decimal(
                0)
            if not operation.is_inner and operation.status == "OK" and operation.brand_name != "Общий платеж":
                opeartion_db = Operation(
                    bank_operation_id=operation.id,
                    bank_name="Yandex",
                    status=operation.status,
                    type=operation.type,
                    group=operation.group,
                    value=money_amount+plus_amount,
                    currency=operation.amount.money.currency if operation.amount.money else '',
                    brand_name=operation.brand_name,
                    category=operation.category,
                    cashback=(
                        operation.cashback
                    ),
                    is_between_owner_accounts=self._is_yandex_operations_between_owner_accounts(
                        operation, owner_phone),
                    created_at=operation.date,
                    raw_data=operation.raw,
                )
                self.add_record(opeartion_db)

    def add_operation_from_telegram(self, operation):
        opeartion_db = Operation(
            bank_operation_id=operation.id,
            bank_name=operation.bank_name,
            status="OK",
            type=operation.type.lower(),
            group=operation.group,
            value=operation.value,
            currency=operation.currency,
            brand_name=None,
            category=operation.category,
            cashback=0,
            is_between_owner_accounts=False,
            created_at=operation.created_at,
            raw_data=operation.raw,
        )
        self.add_record(opeartion_db)

    def _close_products_if_need(self, ids: List[str], bank_name: str, type: AccountTypeEnum):
        account_ids_in_db = self.get_account_ids(
            bank_name=bank_name, type=type)
        account_ids_for_disable = []
        for id in account_ids_in_db:
            if id[0] not in ids:
                account_ids_for_disable.append(id[0])

        if len(account_ids_for_disable) > 0:
            self.change_account_status(
                account_ids_for_disable, StatusEnum.CLOSED)

    def _upsert_tinkoff_accounts_with_cards(self, accounts_with_cards):
        account_ids_from_server = []
        for account in accounts_with_cards:
            account_ids_from_server.append(account.id)

        self._close_products_if_need(
            account_ids_from_server, TINKOFF_BANK_NAME, AccountTypeEnum.CARD)

        for account in accounts_with_cards:
            account_db = Account(
                id=account.id,
                bank_name=TINKOFF_BANK_NAME,
                name=account.name,
                type=AccountTypeEnum.CARD,
                status=StatusEnum.ACTIVE,
                amount=account.amount.value,
                currency=account.amount.currency.name,
                updated_at=datetime.now(),
                raw_data=account.raw,
            )
            self.upsert_account(account_db)

    def _upsert_tinkoff_credits(self, credits):
        account_ids_from_server = []
        for account in credits:
            account_ids_from_server.append(account.id)

        self._close_products_if_need(
            account_ids_from_server, TINKOFF_BANK_NAME, AccountTypeEnum.CREDIT)

        for account in credits:
            account_db = Account(
                id=account.id,
                bank_name=TINKOFF_BANK_NAME,
                name=account.name,
                type=AccountTypeEnum.CREDIT,
                status=StatusEnum.ACTIVE,
                amount=-account.debt_amount.value,
                currency=account.debt_amount.currency.name,
                updated_at=datetime.now(),
                raw_data=account.raw,
            )
            self.upsert_account(account_db)

    def _upsert_multi_deposits(self, multi_deposits):
        account_ids_from_server = []
        for multi_deposit in multi_deposits:
            for deposit in multi_deposit.accounts:
                account_ids_from_server.append(deposit.external_account_number)

        self._close_products_if_need(
            account_ids_from_server, TINKOFF_BANK_NAME, AccountTypeEnum.MULTI_DEPOSIT)

        for multi_deposit in multi_deposits:
            for account in multi_deposit.accounts:
                account_db = Account(
                    id=account.external_account_number,
                    bank_name=TINKOFF_BANK_NAME,
                    name=multi_deposit.name,
                    type=AccountTypeEnum.MULTI_DEPOSIT,
                    status=StatusEnum.ACTIVE,
                    amount=account.amount.value,
                    currency=account.amount.currency.name,
                    updated_at=datetime.now(),
                    raw_data=account.raw,
                )
                self.upsert_account(account_db)

    def _upsert_savings(self, savings):
        account_ids_from_server = []
        for saving in savings:
            account_ids_from_server.append(saving.id)
        self._close_products_if_need(
            account_ids_from_server, TINKOFF_BANK_NAME, AccountTypeEnum.SAVING)

        for saving in savings:
            account_db = Account(
                id=saving.id,
                bank_name=TINKOFF_BANK_NAME,
                name=saving.name,
                type=AccountTypeEnum.SAVING,
                status=StatusEnum.ACTIVE,
                amount=saving.amount.value,
                currency=saving.amount.currency.name,
                updated_at=datetime.now(),
                raw_data=saving.raw,
            )
            self.upsert_account(account_db)

    def upsert_tinkoff_products(self, accounts_with_cards, credits, multi_deposits, savings):
        self._upsert_tinkoff_accounts_with_cards(accounts_with_cards)
        self._upsert_tinkoff_credits(credits)
        self._upsert_multi_deposits(multi_deposits)
        self._upsert_savings(savings)

    def upsert_tinkoff_invest_accounts(self, portfolios):
        account_ids_from_server = []
        for portfolio in portfolios:
            account_ids_from_server.append(portfolio.account_id)
        self._close_products_if_need(
            account_ids_from_server, TINKOFF_BANK_NAME, AccountTypeEnum.INVEST)

        for portfolio in portfolios:
            account_db = Account(
                id=portfolio.account_id,
                bank_name=TINKOFF_BANK_NAME,
                name="Инвестиции",
                type=AccountTypeEnum.INVEST,
                status=StatusEnum.ACTIVE,
                amount=Decimal(portfolio.total_amount_portfolio.units) + Decimal(
                    portfolio.total_amount_portfolio.nano) / Decimal(1_000_000_000),
                currency="RUB",
                updated_at=datetime.now(),
                raw_data={},
            )
            self.upsert_account(account_db)

    def upsert_yandex_accounts(self, yandex_products):
        for product in yandex_products:
            if product.title in list(YANDEX_PRODUCT_TITLE_TO_ACCOUNT_TYPE.keys()):
                account_db = Account(
                    id=YANDEX_PRODUCT_TITLE_TO_ID[product.title],
                    bank_name=YANDEX_BANK_NAME,
                    name=product.title,
                    type=YANDEX_PRODUCT_TITLE_TO_ACCOUNT_TYPE[product.title],
                    status=StatusEnum.ACTIVE,
                    amount=product.amount,
                    currency=product.currency,
                    updated_at=datetime.now(),
                    raw_data={},
                )
                self.upsert_account(account_db)

    def get_operations_by_period(
        self,
        start: datetime | None,
        end: datetime | None,
        type: str
        # period: timedelta | None = timedelta(days=30),
    ):
        operations: List[Operation] = []
        try:
            self._open_session()
            operations = (
                self.session.query(Operation)
                .filter(
                    and_(
                        Operation.type == type,
                        Operation.created_at >= start,
                        Operation.created_at <= end,
                        Operation.is_between_owner_accounts == False,
                    )
                )
                .order_by(desc(Operation.created_at))
                .all()
            )
            return operations
        except Exception as e:
            print(f"Erorr while getting debit operations: {e}")
        finally:
            self._close_session()

    def update_operation_category(self, operation_id, category):
        try:
            self._open_session()
            stmt = (
                update(Operation).
                where(Operation.id == operation_id).
                values(category=category)
            )
            # Выполняем запрос
            self.session.execute(stmt)
            self.session.commit()
            print(f"operation {operation_id} has new category {category}")
        except Exception as e:
            self.session.rollback()
            print(f"Erorr while updating operations: {e}")
            raise
        finally:
            self.session.close()

    def get_balance(self, currency: str):
        try:
            self._open_session()
            stmt = (
                select(func.sum(Account.amount)).where(
                    and_(
                        func.lower(Account.currency) == currency,
                        Account.status == StatusEnum.ACTIVE
                    )

                )
            )

            return self.session.execute(stmt).scalar()
        except Exception as e:
            self.session.rollback()
            print(f"Erorr while get balance: {e}")
            raise
        finally:
            self.session.close()

    def get_cache_balance(self, currency: str):
        try:
            self._open_session()
            stmt = (
                select(func.sum(Account.amount)).where(
                    and_(
                        func.lower(Account.currency) == currency,
                        Account.status == StatusEnum.ACTIVE,
                        Account.type == AccountTypeEnum.CACHE
                    )

                )
            )
            return self.session.execute(stmt).scalar()
        except Exception as e:
            self.session.rollback()
            print(f"Erorr while get balance: {e}")
            raise
        finally:
            self.session.close()

    def upsert_cache_account(self, amount: Decimal, currency: str = 'rub'):
        account_db = Account(
            id='cache',
            bank_name=TINKOFF_BANK_NAME,
            name='cache',
            type=AccountTypeEnum.CACHE,
            status=StatusEnum.ACTIVE,
            amount=amount,
            currency=currency,
            updated_at=datetime.now(),
            raw_data={},
        )
        self.upsert_account(account_db)
