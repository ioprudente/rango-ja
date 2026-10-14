from typing import Protocol
from rango_ja.schemas import ChatResponse


class AgentOrchestrator(Protocol):
    async def handle(
        self,
        *,
        cliente_id: str,
        session_id: str,
        mensagem: str,
    ) -> ChatResponse: ...