from abc import ABC, abstractmethod


class BaseUpdater(ABC):
    def __init__(self, title, client, pg_module):
        self.title = title
        self.client = client
        self.pg_module = pg_module

    @abstractmethod
    async def authorize(self):
        pass

    @abstractmethod
    async def update_balance(self):
        pass

    @abstractmethod
    async def update_operations(self):
        pass
