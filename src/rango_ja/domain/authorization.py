from rango_ja.domain.errors import OrderFromAnotherCustomer
from rango_ja.domain.models import Order


def ensure_owner(order: Order, customer_id: str) -> None:
    if order.cliente_id != customer_id:
        raise OrderFromAnotherCustomer(order.pedido_id)