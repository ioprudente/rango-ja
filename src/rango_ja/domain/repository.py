import json
from functools import lru_cache
from pathlib import Path

from rango_ja.config import get_settings
from rango_ja.domain.errors import OrderNotFound
from rango_ja.domain.models import Order


class OrderRepository:
    def __init__(self, orders_path: str) -> None:
        self._path = Path(orders_path)
        self._by_id: dict[str, Order] = {}
        self._by_customer: dict[str, list[Order]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Arquivo de pedidos não encontrado: {self._path}")

        with self._path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        for entry in raw:
            if "pedido_id" not in entry:
                continue

            entry.setdefault("reembolsos", [])
            order = Order.model_validate(entry)
            
            self._by_id[order.pedido_id] = order
            self._by_customer.setdefault(order.cliente_id, []).append(order)

    def get(self, order_id: str) -> Order:
        order = self._by_id.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    def list_by_customer(self, customer_id: str) -> list[Order]:
        return list(self._by_customer.get(customer_id, []))

    def update(self, order: Order) -> None:
        self._by_id[order.pedido_id] = order
        bucket = self._by_customer.setdefault(order.cliente_id, [])
        for i, o in enumerate(bucket):
            if o.pedido_id == order.pedido_id:
                bucket[i] = order
                return


@lru_cache
def get_repository() -> OrderRepository:
    settings = get_settings()
    return OrderRepository(settings.pedidos_path)