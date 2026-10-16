import json
import logging
from pathlib import Path

from pydantic import ValidationError

from rango_ja.domain.models import Order

logger = logging.getLogger("rango_ja.domain.repository")


class OrderRepository:
    """Carrega pedidos.json uma vez e mantém em memória.

    O repositório é mutável: `order.refunds` cresce conforme
    reembolsos são aprovados/escalados. Em produção, trocar por SQLite.

    Entradas do arquivo que não são pedidos (sem `pedido_id`) são
    ignoradas e registradas em log. Isso cobre o caso do arquivo
    conter anotações soltas, metadados ou texto de prompt injection
    disfarçado de dado (ex.: campo `observacao_entregador`).

    Entradas inválidas (falha de validação) também são ignoradas:
    o app sobe mesmo com um pedido malformado no arquivo, e o
    problema fica registrado no log para investigação.
    """

    def __init__(self, orders_path: str) -> None:
        self._path = Path(orders_path)
        self._by_id: dict[str, Order] = {}
        self.reload()

    def reload(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        entries = raw.values() if isinstance(raw, dict) else raw

        self._by_id = {}
        skipped_non_order = 0
        skipped_invalid = 0
        duplicates = 0

        for index, entry in enumerate(entries):
            # Entradas sem `pedido_id` não são pedidos: são anotações,
            # metadados ou texto de prompt injection. Ignoramos.
            if not isinstance(entry, dict) or not entry.get("pedido_id"):
                skipped_non_order += 1
                logger.warning(
                    "ignoring non-order entry in %s at index=%d keys=%s",
                    self._path,
                    index,
                    (
                        list(entry.keys())
                        if isinstance(entry, dict)
                        else type(entry).__name__
                    ),
                )
                continue

            # Entrada tem cara de pedido, mas pode estar malformada.
            # Não deixamos um registro ruim derrubar o boot.
            try:
                order = Order.model_validate(entry)
            except ValidationError as exc:
                skipped_invalid += 1
                logger.error(
                    "invalid order entry in %s at index=%d pedido_id=%s: %s",
                    self._path,
                    index,
                    entry.get("pedido_id"),
                    exc,
                )
                continue

            if order.order_id in self._by_id:
                duplicates += 1
                logger.warning(
                    "duplicate order_id=%s in %s at index=%d, overwriting",
                    order.order_id,
                    self._path,
                    index,
                )

            self._by_id[order.order_id] = order

        logger.info(
            "loaded %d orders from %s "
            "(skipped_non_order=%d skipped_invalid=%d duplicates=%d)",
            len(self._by_id),
            self._path,
            skipped_non_order,
            skipped_invalid,
            duplicates,
        )

    def get(self, order_id: str) -> Order | None:
        return self._by_id.get(order_id)

    def list_by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._by_id.values() if o.customer_id == customer_id]

    def all(self) -> list[Order]:
        return list(self._by_id.values())