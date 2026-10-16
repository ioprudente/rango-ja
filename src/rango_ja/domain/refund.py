from datetime import datetime, timedelta

from pydantic import BaseModel

from rango_ja.config import Settings
from rango_ja.domain.errors import (
    DuplicateRefund,
    InvalidStatus,
    ItemNotFound,
    OrderNotAccessible,
    OrderNotFound,
    OutsideClaimWindow,
)
from rango_ja.domain.models import (
    BR_TZ,
    REFUND_STATUS_APPROVED,
    REFUND_STATUS_ESCALATED,
    STATUS_CANCELLED_BY_RESTAURANT,
    Order,
    Refund,
)
from rango_ja.domain.repository import OrderRepository

# Valores de "motivo" usados no pedidos.json e nas ferramentas.
REASON_DELAY = "atraso"
REASON_MISSING_ITEM = "item_faltante"
REASON_RESTAURANT_CANCEL = "cancelado_restaurante"

VALID_REASONS = {
    REASON_DELAY,
    REASON_MISSING_ITEM,
    REASON_RESTAURANT_CANCEL,
}


class RefundDecision(BaseModel):
    approved: bool
    amount: float
    reason: str
    escalate_to_human: bool = False


class RefundCalculator:
    """Calcula o valor do reembolso com base nas políticas.

    Regras (sempre aplicadas pelo código, nunca pelo LLM):
      - atraso > 30 min em relação ao previsto: 20% do total
      - item faltante: valor daquele item
      - cancelado pelo restaurante: valor total
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def calculate(
        self, order: Order, reason: str, item: str | None = None
    ) -> float:
        if reason == REASON_DELAY:
            return self._delay(order)
        if reason == REASON_MISSING_ITEM:
            return self._missing_item(order, item)
        if reason == REASON_RESTAURANT_CANCEL:
            return self._restaurant_cancel(order)
        raise InvalidStatus(f"Motivo inválido: {reason!r}")

    def _delay(self, order: Order) -> float:
        if order.delivered_at is None:
            raise InvalidStatus("Pedido ainda não foi entregue.")
        delta = order.delivered_at - order.estimated_at
        threshold = timedelta(minutes=self._settings.delay_threshold_minutes)
        if delta <= threshold:
            raise InvalidStatus("Pedido não ultrapassou o limite de atraso.")
        return round(order.total * self._settings.delay_refund_percent, 2)

    def _missing_item(self, order: Order, item_name: str | None) -> float:
        if not item_name:
            raise ItemNotFound("Informe o nome do item faltante.")
        target = item_name.strip().lower()
        for item in order.items:
            if item.name.lower() == target:
                return round(item.price, 2)
        raise ItemNotFound(f"Item {item_name!r} não consta no pedido.")

    def _restaurant_cancel(self, order: Order) -> float:
        if order.status != STATUS_CANCELLED_BY_RESTAURANT:
            raise InvalidStatus("Pedido não foi cancelado pelo restaurante.")
        return round(order.total, 2)


class RefundService:
    """Orquestra posse, prazo, cálculo e registro do reembolso.

    Não compõe texto para o cliente: isso é responsabilidade da camada
    de ferramentas / orquestrador.
    """

    def __init__(self, settings: Settings, repository: OrderRepository) -> None:
        self._settings = settings
        self._repository = repository
        self._calculator = RefundCalculator(settings)

        reference = datetime.fromisoformat(settings.reference_datetime)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=BR_TZ)
        self._reference = reference

    def request(
        self,
        *,
        customer_id: str,
        order_id: str,
        reason: str,
        item: str | None = None,
    ) -> RefundDecision:
        if reason not in VALID_REASONS:
            raise InvalidStatus(f"Motivo inválido: {reason!r}")

        order = self._repository.get(order_id)
        if order is None:
            raise OrderNotFound(f"Pedido {order_id!r} não encontrado.")
        if order.customer_id != customer_id:
            # Não revelar a distinção "não existe" vs "é de outro cliente".
            raise OrderNotAccessible(
                f"Pedido {order_id!r} não está disponível para esse cliente."
            )

        if order.refunds:
            raise DuplicateRefund(
                f"Pedido {order_id!r} já possui uma solicitação registrada."
            )

        self._check_claim_window(order)

        amount = self._calculator.calculate(order, reason, item)
        approved = amount <= self._settings.max_refund_auto

        order.refunds.append(
            Refund(
                amount=amount,
                reason=reason,
                created_at=self._reference,
                status=(
                    REFUND_STATUS_APPROVED if approved else REFUND_STATUS_ESCALATED
                ),
            )
        )

        return RefundDecision(
            approved=approved,
            amount=amount,
            reason=reason,
            escalate_to_human=not approved,
        )

    def _check_claim_window(self, order: Order) -> None:
        # A reclamação deve ocorrer em até 7 dias após o evento:
        # entrega (atraso / item faltante) ou cancelamento.
        if order.status == STATUS_CANCELLED_BY_RESTAURANT:
            base = order.cancelled_at
        else:
            base = order.delivered_at
        if base is None:
            return
        deadline = base + timedelta(days=self._settings.claim_window_days)
        if self._reference > deadline:
            raise OutsideClaimWindow(
                f"Prazo de reclamação ({self._settings.claim_window_days} dias) "
                f"encerrado."
            )