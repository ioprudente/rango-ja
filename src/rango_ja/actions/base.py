from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from rango_ja.schemas import ToolCall


class ActionRecord(BaseModel):
    session_id: str
    cliente_id: str
    acao: ToolCall
    registrado_em: datetime


class ActionLog(Protocol):
    async def record(self, record: ActionRecord) -> None: ...
    async def list_by_cliente(self, cliente_id: str) -> list[ActionRecord]: ...