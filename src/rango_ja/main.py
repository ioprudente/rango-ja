import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from rango_ja.actions.base import ActionLog, ActionRecord
from rango_ja.agent.base import AgentOrchestrator
from rango_ja.config import Settings, get_settings
from rango_ja.dependencies import ActionsDep, AgentDep, MemoryDep
from rango_ja.memory.base import MemoryStore, Message
from rango_ja.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger("rango_ja")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "startup llm=%s model=%s pedidos=%s politicas=%s",
        settings.llm_provider,
        settings.llm_model,
        settings.pedidos_path,
        settings.politicas_path,
    )
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Rango Já — Agente de Atendimento",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(
    payload: ChatRequest,
    settings: Settings = Depends(get_settings),
    agent: AgentOrchestrator = AgentDep,
    memory: MemoryStore = MemoryDep,
    actions: ActionLog = ActionsDep,
) -> ChatResponse:
    # 1) Persistir a mensagem do usuário antes de agir.
    await memory.append(
        payload.session_id,
        Message(role="user", content=payload.mensagem),
    )

    # 2) Delegar ao orquestrador (LLM + ferramentas + regras de negócio).
    try:
        resposta = await agent.handle(
            cliente_id=payload.cliente_id,
            session_id=payload.session_id,
            mensagem=payload.mensagem,
        )
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo esgotado ao falar com o provedor de LLM.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("falha no orquestrador: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao processar a mensagem.",
        )

    # 3) Registrar resposta + ações executadas.
    await memory.append(
        payload.session_id,
        Message(role="assistant", content=resposta.resposta),
    )
    for acao in resposta.acoes:
        await actions.record(
            ActionRecord(
                session_id=payload.session_id,
                cliente_id=payload.cliente_id,
                acao=acao,
                registrado_em=datetime.now(timezone.utc),
            )
        )

    return resposta


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})