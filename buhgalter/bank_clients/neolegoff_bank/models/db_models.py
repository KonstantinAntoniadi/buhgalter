from sqlalchemy import Column, Numeric, String, DateTime, Boolean, func, Enum, BigInteger
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import enum

Base = declarative_base()


class StatusEnum(enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class AccountTypeEnum(enum.Enum):
    INVEST = "invest"
    SAVING = "saving"
    DEPOSIT = "depostit"
    MULTI_DEPOSIT = "multi_depostit"
    CREDIT = "credit"
    CARD = "card"
    BONUS = "bonus"
    CACHE = "cache"


class Operation(Base):
    __tablename__ = "operations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bank_operation_id = Column(String, index=True)
    bank_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    type = Column(String, nullable=False)
    group = Column(String, nullable=False)
    value = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String, nullable=False)
    brand_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    cashback = Column(Numeric(precision=10, scale=2), nullable=False)
    is_between_owner_accounts = Column(Boolean, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    raw_data = Column(JSONB, nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)
    type = Column(Enum(AccountTypeEnum), nullable=False)
    name = Column(String, nullable=True)
    status = Column(Enum(StatusEnum), nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    raw_data = Column(JSONB, nullable=False)
