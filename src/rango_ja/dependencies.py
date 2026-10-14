from fastapi import Depends

from rango_ja.actions.base import ActionLog
from rango_ja.actions.in_memory import InMemoryActionLog
from rango_ja.agent.base import AgentOrchestrator
from rango_ja.agent.fake import FakeOrchestrator
from rango_ja.config import Settings, get_settings
from rango_ja.memory.base import MemoryStore
from rango_ja.memory.in_memory import InMemoryMemoryStore

_memory_singleton: MemoryStore = InMemoryMemoryStore()
_actions_singleton: ActionLog = InMemoryActionLog()
_agent_singleton: AgentOrchestrator = FakeOrchestrator()


def get_memory() -> MemoryStore:
    return _memory_singleton


def get_action_log() -> ActionLog:
    return _actions_singleton


def get_agent() -> AgentOrchestrator:
    return _agent_singleton


SettingsDep = Depends(get_settings)
MemoryDep = Depends(get_memory)
ActionsDep = Depends(get_action_log)
AgentDep = Depends(get_agent)
