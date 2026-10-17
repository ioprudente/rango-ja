from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, AliasChoices


class RefundReason(str, Enum):
    DELAY = "atraso"
    MISSING_ITEM = "item_faltante"
    RESTAURANT_CANCELLATION = "cancelamento_restaurante"


class Item(BaseModel):
    nome: str
    preco: float


class Refund(BaseModel):
    valor: float
    motivo: str
    data: datetime


class Order(BaseModel):
    pedido_id: str
    cliente_id: str
    restaurante: str
    status: str
    # O AliasChoices faz o Pydantic aceitar tanto 'itens' quanto 'items' no JSON
    itens: list[Item] = Field(
        default_factory=list, 
        validation_alias=AliasChoices("itens", "items")
    )
    taxa_entrega: float = 0.0
    total: float
    previsto_para: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    cancelado_em: Optional[datetime] = None
    reembolsos: list[Refund] = Field(default_factory=list)

    def has_refund(self) -> bool:
        return len(self.reembolsos) > 0

    def get_item_by_name(self, name: str) -> Optional[Item]:
        target = name.strip().lower()
        for item in self.itens:
            if item.nome.strip().lower() == target:
                return item
        return None
