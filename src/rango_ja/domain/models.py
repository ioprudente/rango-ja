from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, AliasChoices

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
    model_config = ConfigDict(populate_by_name=True)
    
    pedido_id: str
    cliente_id: str
    restaurante: str
    status: str
    itens: list[Item] = Field(default_factory=list, validation_alias=AliasChoices("itens", "items"))
    taxa_entrega: float = 0.0
    total: float
    previsto_para: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    cancelado_em: Optional[datetime] = None
    reembolsos: list[Refund] = Field(default_factory=list)
    observacao_entregador: Optional[str] = None

    def has_refund(self) -> bool:
        return len(self.reembolsos) > 0

    def get_item_by_name(self, name: str) -> Optional[Item]:
        target = name.strip().lower()
        target_words = set(target.split())
        for item in self.itens:
            # Compara palavras inteiras. Evita que "a" case com tudo, mas acha "refrigerante" em "Refrigerante lata"
            if target == item.nome.strip().lower() or target_words.issubset(set(item.nome.strip().lower().split())):
                return item
        return None
