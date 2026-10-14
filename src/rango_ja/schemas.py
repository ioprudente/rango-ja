from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    cliente_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Usuário autenticado. Tratado como confiável.",
    )
    session_id: str = Field(..., min_length=1, max_length=128)
    mensagem: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Texto do cliente. Tratado como NÃO confiável.",
    )


ToolResult = Literal["ok", "erro", "negado", "aprovado", "escalado", "recusado"]


class ToolCall(BaseModel):
    ferramenta: str
    argumentos: dict[str, Any] = Field(default_factory=dict)
    resultado: ToolResult = "ok"


class ChatResponse(BaseModel):
    resposta: str
    acoes: list[ToolCall] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    llm_provider: str
    llm_model: str
