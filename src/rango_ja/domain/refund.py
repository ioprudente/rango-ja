from datetime import datetime, timedelta

from rango_ja.config import Settings, get_settings
from rango_ja.domain.errors import (
    ClaimOutOfTimeframe,
    DuplicateRefund,
    ItemNotFoundInOrder,
    UnsupportedReason,
    ValueExceedsLimit,
)
from rango_ja.domain.models import Order, RefundReason


class RefundResult:
    def __init__(self, value: float, approved: bool, reason: RefundReason) -> None:
        self.value = value
        self.approved = approved
        self.reason = reason


def _reference_now(settings: Settings) -> datetime:
    return datetime.fromisoformat(settings.reference_datetime).replace(tzinfo=None)


def _validate_timeframe(order: Order, settings: Settings) -> None:
    if order.entregue_em is None:
        return
    
    now = _reference_now(settings)
    limit = order.entregue_em + timedelta(days=settings.claim_window_days)
    if now > limit:
        raise ClaimOutOfTimeframe(order.pedido_id)


def _calculate_delay_minutes(order: Order) -> float:
    if order.entregue_em is None or order.previsto_para is None:
        return 0.0
    delta = order.entregue_em - order.previsto_para
    return delta.total_seconds() / 60.0


def calculate_refund(
    order: Order,
    reason: RefundReason,
    item_name: str | None = None,
    settings: Settings | None = None,
) -> RefundResult:
    settings = settings or get_settings()

    if order.has_refund():
        raise DuplicateRefund(order.pedido_id)

    _validate_timeframe(order, settings)

    value = 0.0

    if reason is RefundReason.DELAY:
        minutes = _calculate_delay_minutes(order)
        if minutes <= settings.delay_threshold_minutes:
            return RefundResult(value=0.0, approved=False, reason=reason)
        value = round(order.total * settings.delay_refund_percent, 2)

    elif reason is RefundReason.MISSING_ITEM:
        if not item_name:
            raise UnsupportedReason("item_faltante exige o nome do item.")
        item = order.get_item_by_name(item_name)
        if item is None:
            raise ItemNotFoundInOrder(order.pedido_id, item_name)
        value = round(item.preco, 2)

    elif reason is RefundReason.RESTAURANT_CANCELLATION:
        value = round(order.total, 2)

    else:
        raise UnsupportedReason(str(reason))

    if value > settings.max_refund_auto:
        raise ValueExceedsLimit(value, settings.max_refund_auto)

    return RefundResult(value=value, approved=True, reason=reason)