class DomainError(Exception):
    """Base para erros de regra de negócio. As mensagens podem chegar ao cliente."""

class OrderNotFound(DomainError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Não encontrei o pedido {order_id} na sua conta.")
        self.order_id = order_id

class OrderFromAnotherCustomer(DomainError):
    """Mesma frase de OrderNotFound: não revela que o pedido existe."""
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Não encontrei o pedido {order_id} na sua conta.")
        self.order_id = order_id

class ClaimOutOfTimeframe(DomainError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"O pedido {order_id} está fora do prazo de 7 dias após a entrega para reclamações.")
        self.order_id = order_id

class DuplicateRefund(DomainError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"O pedido {order_id} já possui um reembolso registrado; cada pedido pode ter no máximo um.")
        self.order_id = order_id

class ItemNotFoundInOrder(DomainError):
    def __init__(self, order_id: str, item: str) -> None:
        super().__init__(f"Não encontrei o item '{item}' no pedido {order_id}.")
        self.order_id = order_id
        self.item = item

class ValueExceedsLimit(DomainError):
    def __init__(self, value: float, limit: float) -> None:
        super().__init__(f"Reembolso de R$ {value:.2f} excede o limite de R$ {limit:.2f}.")
        self.value = value
        self.limit = limit

class UnsupportedReason(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.reason = message
