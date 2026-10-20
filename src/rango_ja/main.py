import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from rango_ja.actions.base import ActionLog, ActionRecord
from rango_ja.agent.base import AgentOrchestrator
from rango_ja.config import Settings, get_settings
from rango_ja.dependencies import ActionsDep, AgentDep
from rango_ja.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger("rango_ja")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Rango Já", version="0.1.0", lifespan=lifespan)

@app.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", llm_provider=settings.llm_provider, llm_model=settings.llm_model)

@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(payload: ChatRequest, agent: AgentOrchestrator = AgentDep, actions: ActionLog = ActionsDep) -> ChatResponse:
    try:
        resposta = await agent.handle(cliente_id=payload.cliente_id, session_id=payload.session_id, mensagem=payload.mensagem)
    except Exception as exc:
        logger.exception("falha no orquestrador")
        raise HTTPException(status_code=502, detail="Falha ao processar a mensagem.")

    now = datetime.fromisoformat(get_settings().reference_datetime)
    for acao in resposta.acoes:
        executada = (
            (acao.ferramenta == "solicitar_reembolso" and acao.resultado == "aprovado")
            or (acao.ferramenta == "escalar_para_humano" and acao.resultado == "ok")
        )
        if executada:
            await actions.record(ActionRecord(session_id=payload.session_id, cliente_id=payload.cliente_id, acao=acao, registrado_em=now))
    return resposta
