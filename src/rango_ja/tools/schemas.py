from typing import Optional
from pydantic import BaseModel, Field
from rango_ja.domain.models import RefundReason


class ConsultOrderArgs(BaseModel):
    pedido_id: str = Field(..., description="ID do pedido (ex: P1001)")


class ListOrdersArgs(BaseModel):
    pass


class SearchPoliciesArgs(BaseModel):
    pergunta: str = Field(..., description="Dúvida do cliente sobre as políticas")


class RequestRefundArgs(BaseModel):
    pedido_id: str = Field(..., description="ID do pedido")
    motivo: RefundReason = Field(..., description="Motivo do reembolso")
    item: Optional[str] = Field(
        None, description="Nome do item (obrigatório se motivo for item_faltante)"
    )


class EscalateToHumanArgs(BaseModel):
    pedido_id: Optional[str] = Field(None, description="ID do pedido, se aplicável")
    motivo: str = Field(..., description="Motivo do escalonamento")
