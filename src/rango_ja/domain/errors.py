class DomainError(Exception):
    """Base para todos os erros de regra de negócio."""


class OrderNotFound(DomainError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Pedido {order_id} não encontrado.")
        self.order_id = order_id


class OrderFromAnotherCustomer(DomainError):
    """Nunca revelar que o pedido existe para outro cliente."""
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Pedido {order_id} não pertence a este cliente.")
        self.order_id = order_id


class ClaimOutOfTimeframe(DomainError):
    def __init__(self, order_id: str) -> None:
        super().__init__(
            f"Pedido {order_id} está fora do prazo de 7 dias para reclamação."
        )
        self.order_id = order_id


class DuplicateRefund(DomainError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Pedido {order_id} já possui um reembolso registrado.")
        self.order_id = order_id


class ValueExceedsLimit(DomainError):
    """Sinaliza que o reembolso precisa ser escalado, não recusado."""
    def __init__(self, value: float, limit: float) -> None:
        super().__init__(
            f"Reembolso de R$ {value:.2f} excede o limite de R$ {limit:.2f}."
        )
        self.value = value
        self.limit = limit


class UnsupportedReason(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Motivo '{reason}' não é suportado pelo sistema.")
        self.reason = reason


class ItemNotFoundInOrder(DomainError):
    def __init__(self, order_id: str, item: str) -> None:
        super().__init__(f"Item '{item}' não encontrado no pedido {order_id}.")
        self.order_id = order_id
        self.item = item