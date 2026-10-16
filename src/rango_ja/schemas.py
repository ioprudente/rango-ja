from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str = Field(
        ...,
        alias="cliente_id",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Usuário autenticado. Tratado como confiável.",
    )
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(
        ...,
        alias="mensagem",
        min_length=1,
        max_length=4000,
        description="Texto do cliente. Tratado como NÃO confiável.",
    )


ToolResult = Literal["ok", "erro", "negado", "aprovado", "escalado", "recusado"]


class ToolCall(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool: str = Field(..., alias="ferramenta")
    arguments: dict[str, Any] = Field(default_factory=dict, alias="argumentos")
    result: ToolResult = Field(default="ok", alias="resultado")


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(..., alias="resposta")
    actions: list[ToolCall] = Field(default_factory=list, alias="acoes")


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    llm_provider: str
    llm_model: str