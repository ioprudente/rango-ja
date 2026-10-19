from datetime import datetime, timedelta
from rango_ja.config import Settings, get_settings
from rango_ja.domain.errors import *
from rango_ja.domain.models import Order, RefundReason

class RefundResult:
    def __init__(self, value: float, approved: bool, reason: RefundReason) -> None:
        self.value = value
        self.approved = approved
        self.reason = reason

def _reference_now(settings: Settings) -> datetime:
    return datetime.fromisoformat(settings.reference_datetime).replace(tzinfo=None)

def _validate_timeframe(order: Order, settings: Settings) -> None:
    if order.entregue_em is None: return
    if _reference_now(settings) > order.entregue_em + timedelta(days=settings.claim_window_days):
        raise ClaimOutOfTimeframe(order.pedido_id)

def calculate_refund(order: Order, reason: RefundReason, item_name: str | None = None, settings: Settings | None = None) -> RefundResult:
    settings = settings or get_settings()
    if order.has_refund(): raise DuplicateRefund(order.pedido_id)
    _validate_timeframe(order, settings)

    value = 0.0
    if reason is RefundReason.DELAY:
        if order.status != "entregue":
            raise UnsupportedReason("O pedido ainda não foi entregue para avaliar atraso.")
        if order.entregue_em and order.previsto_para:
            delta = order.entregue_em - order.previsto_para
            if delta.total_seconds() / 60.0 <= settings.delay_threshold_minutes:
                return RefundResult(0.0, False, reason)
        value = round(order.total * settings.delay_refund_percent, 2)
    
    elif reason is RefundReason.MISSING_ITEM:
        if order.status != "entregue":
            raise UnsupportedReason("O pedido ainda não foi entregue para avaliar item faltante.")
        if not item_name: raise DomainError("Informe o nome do item que faltou para prosseguir com o reembolso.")
        item = order.get_item_by_name(item_name)
        if not item: raise ItemNotFoundInOrder(order.pedido_id, item_name)
        value = round(item.preco, 2)
        
    elif reason is RefundReason.RESTAURANT_CANCELLATION:
        if order.status != "cancelado_restaurante":
            raise UnsupportedReason("O restaurante não cancelou este pedido.")
        value = round(order.total, 2)
    
    if value > settings.max_refund_auto:
        raise ValueExceedsLimit(value, settings.max_refund_auto)
    return RefundResult(value, True, reason)
