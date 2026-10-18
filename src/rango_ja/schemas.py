from typing import Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    cliente_id: str = Field(..., description="ID do cliente autenticado")
    session_id: str = Field(..., description="ID da sessão de conversa")
    mensagem: str = Field(..., description="Mensagem enviada pelo cliente")


class ToolCall(BaseModel):
    ferramenta: str
    argumentos: dict[str, Any]
    resultado: str


class ChatResponse(BaseModel):
    resposta: str
    acoes: list[ToolCall] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_model: str
