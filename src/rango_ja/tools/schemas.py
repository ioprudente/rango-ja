from pydantic import BaseModel, Field

class ConsultOrderArgs(BaseModel):
    pedido_id: str = Field(..., description="ID do pedido (ex: P1001)")

class ListOrdersArgs(BaseModel):
    pass

class SearchPoliciesArgs(BaseModel):
    pergunta: str = Field(..., description="Dúvida do cliente sobre as políticas")

class RequestRefundArgs(BaseModel):
    pedido_id: str = Field(..., description="ID do pedido")
    motivo: str = Field(..., description="Motivo: 'atraso', 'item_faltante', 'cancelamento_restaurante'")
    item: str = Field("nao_aplicavel", description="Nome do item. Obrigatório para item_faltante, senão use 'nao_aplicavel'")

class EscalateToHumanArgs(BaseModel):
    pedido_id: str = Field("", description="ID do pedido, se aplicável")
    motivo: str = Field(..., description="Motivo do escalonamento")
