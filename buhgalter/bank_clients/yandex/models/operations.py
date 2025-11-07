
from datetime import datetime
from pydantic import BaseModel, ValidationError, Field, root_validator, validator
from types import UnionType
from typing import Any, TypeVar, Literal, Optional, List
from ssl import SSLWantReadError
from httpx import Response
from dateutil import parser
from decimal import Decimal

Func = TypeVar("Func")


def pydantic_auto_detect(models: list[type[BaseModel]], data: dict) -> BaseModel:
    for model in models:
        try:
            model_data = model(**data)
            return model_data
        except Exception as e:  # ValidationError
            print(e)
            continue
    raise ValueError(f"Data doesn't match any model")


def prepare_response():
    def decorate(f: Func) -> Func:
        async def wrapper(self, *args, **kwargs):
            try:
                try:
                    response: Response | Any = await f(self, *args, **kwargs)
                except (SSLWantReadError,) as e:
                    response: Response | Any = await f(self, *args, **kwargs)

                return_type = f.__annotations__["return"]

                if issubclass(type(return_type), type) and issubclass(
                    return_type, PayloadModel
                ):  # extract payload from response model
                    model = BaseApiResponse(**response.json())

                    if model.is_success:
                        payload_model = f.__annotations__["return"]
                        return payload_model(payload=model.payload)
                elif issubclass(type(return_type), UnionType):
                    try:
                        model = pydantic_auto_detect(
                            return_type.__args__, response.json())
                    except ValueError:
                        model = return_type(**response.json())
                else:
                    model = return_type(**response.json())

                return model

                return response
            except ValidationError as e:
                print(e)
                print(f"ValidationError = {response.json()}")

        return wrapper

    return decorate


class PayloadModel(BaseModel):
    ...

    @root_validator(pre=True)
    def unpack_fields(cls, values: dict[str, Any]):
        def fields_iterator():
            return cls.__fields__.items()

        payload = values.get("payload", {})

        for field_name, field_info in fields_iterator():
            if field_info.alias in payload:
                values[field_info.alias] = payload.get(field_info.alias)

        return values


class BaseApiResponse(BaseModel):
    data: dict = Field(..., alias="data")


class Money(BaseModel):
    amount: Decimal = Field(..., alias="amount")
    currency: str = Field(..., alias="currency")


class Amount(BaseModel):
    money: Optional[Money] = Field(..., alias="money")
    plus: Optional[Decimal] = Field(..., alias="plus")


class OperationItem(BaseModel):
    id: str = Field(..., alias="id")

    @root_validator(pre=True)
    def add_raw(cls, values: dict):
        values["date"] = parser.isoparse(values["date"])
        return values


class GetTransactionsFeedView(BaseModel):
    cursor: str = Field(..., alias="cursor")
    items: List[OperationItem] = Field(..., alias="items")
    is_empty_by_filter: bool = Field(..., alias="isEmptyByFilter")


class Data(BaseModel):
    result: GetTransactionsFeedView = Field(...,
                                            alias="getTransactionsFeedView")


class OperationsResponse(BaseModel):
    data: Data = Field(..., alias="data")


class AdditionalField(BaseModel):
    name: str = Field(..., alias="name")
    value: str = Field(..., alias="value")


class AdditionalFields(BaseModel):
    additional_fields: List[AdditionalField] = Field(
        ..., alias="additionalFields")


class Operation(BaseModel):
    id: str = Field(..., alias="id")
    date: datetime
    status: str = Field(..., alias="statusCode")
    amount: Amount = Field(..., alias="amount")
    type: Optional[Literal["debit", "credit"]] = Field(...)
    group: str = None
    comment: Optional[str] = Field(..., alias="comment")
    cashback: Decimal
    category: str = None
    brand_name: str = None
    is_inner: bool
    sender_phone: Optional[str]
    recipients_phone: Optional[str]

    raw: dict[str, Any]

    @root_validator(pre=True)
    def add_raw(cls, values: dict):
        if "directionV2" in values:
            values["type"] = values["directionV2"]
        elif "direction" in values:
            values["type"] = values["direction"]
        values["raw"] = values.copy()
        values["date"] = parser.isoparse(values["date"])
        add_fields = values["additionalFields"]["additionalFields"]
        values["is_inner"] = False
        values["sender_phone"] = False
        values["recipients_phone"] = False
        for field in add_fields:
            field_name = field["name"]
            if field_name == "Категория":
                values["category"] = field.get("value", None)
                if values.get("direction", None) == "CREDIT" or values.get("directionV2", None) == "CREDIT":
                    values["group"] = "income"
                elif values.get("direction", None) == "DEBIT" or values.get("directionV2", None) == "DEBIT":
                    values["group"] = "pay"
            elif field_name == "Перевод с номера телефона":
                values["sender_phone"] = field["value"]
            elif field_name == "Перевод по номеру телефона":
                values["recipients_phone"] = field["value"]
            elif field_name == "":
                if field["value"] == "С карты Пэй" or field["value"] == "На карту Пэй":
                    values["is_inner"] = True

        if values.get("group", None) is None:
            values["group"] = "transfer"

        values["brand_name"] = values["title"].get("plain", None)

        cashback_amount = Decimal(0)
        services_cachback = values["cashback"].get(
            "servicesCashback", []) if values["cashback"] else []
        for cashback in services_cachback:
            plus = Decimal(cashback.get("cashbackInfo", {}).get(
                "totalValue", {}).get("plus", 0))
            cashback_amount += plus

        values["cashback"] = cashback_amount

        return values

    @validator('type', pre=True)
    def convert_type(cls, value):
        if value == "DEBIT":
            return "debit"
        elif value == "CREDIT":
            return "credit"
        elif value is None:
            return None
        raise ValueError(f"Invalid transaction type = {value}")

    @validator('status', pre=True)
    def convert_status(cls, value):
        if value == "CLEAR":
            return "OK"
        else:
            return value


class BankUser(BaseModel):
    id: str = Field(..., alias="id")
    operation: Operation = Field(..., alias="operationV2")


class OperationData(BaseModel):
    bank_user: BankUser = Field(..., alias="bankUser")


class OperationResponse(BaseModel):
    data: OperationData = Field(..., alias="data")
