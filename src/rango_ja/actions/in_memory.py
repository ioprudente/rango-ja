from collections import defaultdict

from rango_ja.actions.base import ActionLog, ActionRecord


class InMemoryActionLog:
    def __init__(self) -> None:
        self._by_cliente: dict[str, list[ActionRecord]] = defaultdict(list)

    async def record(self, record: ActionRecord) -> None:
        self._by_cliente[record.cliente_id].append(record)

    async def list_by_cliente(self, cliente_id: str) -> list[ActionRecord]:
        return list(self._by_cliente[cliente_id])
