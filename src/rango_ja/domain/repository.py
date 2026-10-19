import json
from functools import lru_cache
from pathlib import Path
from rango_ja.config import get_settings
from rango_ja.domain.errors import OrderNotFound
from rango_ja.domain.models import Order

class OrderRepository:
    def __init__(self, orders_path: str) -> None:
        self._path = Path(orders_path)
        self._state_path = Path("data/pedidos_state.json")
        self._by_id: dict[str, Order] = {}
        self._by_customer: dict[str, list[Order]] = {}
        self._load()

    def _load(self) -> None:
        # Se o estado persistido existir, carrega ele. Se não, carrega o original.
        path_to_load = self._state_path if self._state_path.exists() else self._path
        
        if not path_to_load.exists():
            raise FileNotFoundError(f"Arquivo de pedidos não encontrado: {path_to_load}")

        with path_to_load.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        for entry in raw:
            if "pedido_id" not in entry: continue
            entry.setdefault("reembolsos", [])
            order = Order.model_validate(entry)
            self._by_id[order.pedido_id] = order
            self._by_customer.setdefault(order.cliente_id, []).append(order)

    def _save_state(self) -> None:
        # Salva o estado atualizado no disco
        raw_data = [json.loads(o.model_dump_json()) for o in self._by_id.values()]
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, order_id: str) -> Order:
        order = self._by_id.get(order_id)
        if order is None: raise OrderNotFound(order_id)
        return order

    def list_by_customer(self, customer_id: str) -> list[Order]:
        return list(self._by_customer.get(customer_id, []))

    def update(self, order: Order) -> None:
        self._by_id[order.pedido_id] = order
        bucket = self._by_customer.setdefault(order.cliente_id, [])
        for i, o in enumerate(bucket):
            if o.pedido_id == order.pedido_id:
                bucket[i] = order
                break
        self._save_state() # <-- Salva no JSON

@lru_cache
def get_repository() -> OrderRepository:
    return OrderRepository(get_settings().pedidos_path)
