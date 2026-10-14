from collections import defaultdict

from rango_ja.memory.base import MemoryStore, Message


class InMemoryMemoryStore:
    def __init__(self, max_messages: int = 50) -> None:
        self._data: dict[str, list[Message]] = defaultdict(list)
        self._max = max_messages

    async def get_history(self, session_id: str) -> list[Message]:
        return list(self._data[session_id])

    async def append(self, session_id: str, message: Message) -> None:
        bucket = self._data[session_id]
        bucket.append(message)
        if len(bucket) > self._max:
            del bucket[: len(bucket) - self._max]

    async def clear(self, session_id: str) -> None:
        self._data.pop(session_id, None)
