from fastapi import Depends

from rango_ja.actions.base import ActionLog
from rango_ja.actions.in_memory import InMemoryActionLog
from rango_ja.agent.base import AgentOrchestrator
from rango_ja.agent.fake import FakeOrchestrator
from rango_ja.config import Settings, get_settings
from rango_ja.domain.refund import RefundService
from rango_ja.domain.repository import OrderRepository
from rango_ja.memory.base import MemoryStore
from rango_ja.memory.in_memory import InMemoryMemoryStore

_memory_singleton: MemoryStore = InMemoryMemoryStore()
_actions_singleton: ActionLog = InMemoryActionLog()
_agent_singleton: AgentOrchestrator = FakeOrchestrator()

_settings_singleton: Settings = get_settings()
_order_repository_singleton = OrderRepository(_settings_singleton.orders_path)
_refund_service_singleton = RefundService(
    _settings_singleton, _order_repository_singleton
)


def get_memory() -> MemoryStore:
    return _memory_singleton


def get_action_log() -> ActionLog:
    return _actions_singleton


def get_agent() -> AgentOrchestrator:
    return _agent_singleton


def get_order_repository() -> OrderRepository:
    return _order_repository_singleton


def get_refund_service() -> RefundService:
    return _refund_service_singleton



SettingsDep = Depends(get_settings)
MemoryDep = Depends(get_memory)
ActionsDep = Depends(get_action_log)
AgentDep = Depends(get_agent)
OrderRepoDep = Depends(get_order_repository)
RefundServiceDep = Depends(get_refund_service)