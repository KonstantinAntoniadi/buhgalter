from decimal import Decimal
from typing import Any, List, Literal

from pydantic import BaseModel, Field, root_validator

from bank_clients.neolegoff_bank.models.api_response_base import PayloadModel
from bank_clients.neolegoff_bank.models.base import Amount, Currency
from bank_clients.neolegoff_bank.models.products.cards import CardExternal, CardInternal


class AccountBase(BaseModel):
    id: str
    name: str
    type: str = Field(..., alias="accountType")

    # currency: Currency
    # amount: Amount = Field(..., alias="moneyAmount")
    # income_amount: Amount = Field(..., alias="totalIncome")
    # expense_amount: Amount = Field(..., alias="totalExpense")

    # creation_date: date

    # hidden: bool

    raw: dict[str, Any]

    @root_validator(pre=True)
    def root_creation(cls, values: dict):
        # creation_ms = values.get("creationDate").get("milliseconds")
        values["raw"] = values.copy()
        # values["creation_date"] = datetime.fromtimestamp(creation_ms / 1000).date()
        return values


class AccountInternal(AccountBase):
    tariff_name: str = Field(..., alias="marketingName")
    tariff_id: str = Field(..., alias="tariffFileHash")

    group: str = Field(..., alias="accountGroup")
    rate: int
    part_number: str = Field(..., alias="partNumber")


class AccountExternal(AccountBase):
    type: Literal["ExternalAccount"] = Field(..., alias="accountType")


class AccountMultiDeposit(AccountBase):
    type: Literal["MultiDeposit"] = Field(..., alias="accountType")


class AccountSaving(AccountBase):
    type: Literal["Saving"] = Field(..., alias="accountType")

    name: str = Field(..., alias="name")
    amount: Amount = Field(..., alias="moneyAmount")


class AccountWithCards(AccountInternal):
    type: Literal["Current", "Telecom"] = Field(..., alias="accountType")

    amount: Amount = Field(..., alias="moneyAmount")
    number: str = Field(None, alias="externalAccountNumber")
    purchases_sum: Decimal = Field(..., alias="sumPurchases")
    cards: list[CardInternal | CardExternal] = Field(..., alias="cardNumbers")


class AccountCredit(AccountInternal):
    type: Literal["Credit"] = Field(..., alias="accountType")
    currency: Currency

    debt_amount: Amount = Field(..., alias="debtAmount")


class AccountMultiDepositItem(BaseModel):
    external_account_number: str = Field(..., alias="externalAccountNumber")
    amount: Amount = Field(..., alias="moneyAmount")
    interest: Amount = Field(..., alias="interest")
    deposit_rate: Decimal = Field(..., alias="depositRate")

    raw: dict[str, Any]

    @root_validator(pre=True)
    def root_creation(cls, values: dict):
        values["raw"] = values.copy()
        return values


class AccountMultiDeposit(AccountBase):
    type: Literal["MultiDeposit"] = Field(..., alias="accountType")

    name: str = Field(..., alias="name")
    accounts: List[AccountMultiDepositItem] = Field(..., alias="accounts")


class AccountCashLoan(AccountBase):
    type: Literal["CashLoan"] = Field(..., alias="accountType")


class Accounts(PayloadModel):
    accounts: list[
        AccountWithCards
        | AccountCredit
        | AccountSaving
        | AccountMultiDeposit
        | AccountCashLoan
        | AccountExternal
        | AccountBase
    ] = Field(alias="payload")

    def __iter__(self):
        return iter(self.accounts)

    def __getitem__(
        self, item
    ) -> (
        AccountWithCards
        | AccountCredit
        | AccountSaving
        | AccountCashLoan
        | AccountMultiDeposit
        | AccountExternal
        | AccountBase
    ):
        # by tinkoff_id
        if isinstance(item, str) and item.isdigit() and len(item) == 10:
            return [a for a in self.accounts if a.id == item][0]
        # by account number
        if isinstance(item, str) and item.isdigit() and len(item) == 20:
            return [
                a for a in self.accounts if "number" in dir(a) and a.number == item
            ][0]
        # by account name
        if isinstance(item, str):
            return [a for a in self.accounts if a.name == item][0]

        raise KeyError("Invalid item")

        # 40817810000023685898

    @property
    def currents(self):
        return Accounts(payload=[a for a in self.accounts if a.type == "Current"])

    @property
    def cash_loans(self):
        return Accounts(payload=[a for a in self.accounts if a.type == "CashLoan"])

    @property
    def credits(self):
        return Accounts(payload=[a for a in self.accounts if a.type == "Credit"])

    @property
    def externals(self):
        return Accounts(
            payload=[a for a in self.accounts if a.type == "ExternalAccount"]
        )

    @property
    def savings(self):
        return Accounts(payload=[a for a in self.accounts if a.type == "Saving"])

    @property
    def multi_deposits(self):
        return Accounts(payload=[a for a in self.accounts if a.type == "MultiDeposit"])
