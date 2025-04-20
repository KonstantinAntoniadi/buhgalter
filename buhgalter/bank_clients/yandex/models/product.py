from decimal import Decimal


class YandexProduct:
    def __init__(self, id: str, title: str, amount: Decimal, currency: str):
        self.id = id
        self.title = title
        self.amount = amount
        self.currency = currency
