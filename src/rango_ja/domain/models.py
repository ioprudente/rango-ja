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
    # extra="forbid" mantém a segurança contra campos maliciosos
    # populate_by_name=True permite usar o nome do campo no Python
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    
    pedido_id: str
    cliente_id: str
    restaurante: str
    status: str
    
    # AliasChoices resolve o problema: aceita "itens" ou "items" no JSON
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
    observacao_entregador: Optional[str] = None

    def has_refund(self) -> bool:
        return len(self.reembolsos) > 0

    def get_item_by_name(self, name: str) -> Optional[Item]:
        target = name.strip().lower()
        for item in self.itens:
            if target in item.nome.strip().lower() or item.nome.strip().lower() in target:
                return item
        return None
