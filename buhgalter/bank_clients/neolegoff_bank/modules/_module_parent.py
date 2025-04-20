class AioNeolegoffModuleParent:
    def __init__(self, neolegoff: "AioNeolegoff"):
        from bank_clients.neolegoff_bank.modules import AioNeolegoff

        self._neolegoff: AioNeolegoff = neolegoff
        self.core = self._neolegoff.core
