from typing import Protocol

from pydantic import BaseModel


class Message(BaseModel):
    role: str  # "user" | "assistant" | "tool"
    content: str


class MemoryStore(Protocol):
    async def get_history(self, session_id: str) -> list[Message]: ...
    async def append(self, session_id: str, message: Message) -> None: ...
    async def clear(self, session_id: str) -> None: ...
