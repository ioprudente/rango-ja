import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from rango_ja.actions.base import ActionLog, ActionRecord
from rango_ja.agent.base import AgentOrchestrator
from rango_ja.config import get_settings
from rango_ja.dependencies import (
    ActionsDep,
    AgentDep,
    MemoryDep,
    get_order_repository,
)
from rango_ja.memory.base import MemoryStore, Message
from rango_ja.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger("rango_ja")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "startup llm=%s model=%s orders=%s policies=%s",
        settings.llm_provider,
        settings.llm_model,
        settings.orders_path,
        settings.policies_path,
    )
    repo = get_order_repository()
    logger.info("orders loaded at startup: %d", len(repo.all()))
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Rango Já — Agente de Atendimento",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health(settings=Depends(get_settings)) -> HealthResponse:
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
    agent: AgentOrchestrator = AgentDep,
    memory: MemoryStore = MemoryDep,
    actions: ActionLog = ActionsDep,
) -> ChatResponse:
    await memory.append(
        payload.session_id,
        Message(role="user", content=payload.message),
    )

    try:
        response = await agent.handle(
            customer_id=payload.customer_id,
            session_id=payload.session_id,
            message=payload.message,
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

    await memory.append(
        payload.session_id,
        Message(role="assistant", content=response.answer),
    )
    for action in response.actions:
        await actions.record(
            ActionRecord(
                session_id=payload.session_id,
                customer_id=payload.customer_id,
                action=action,
                recorded_at=datetime.now(timezone.utc),
            )
        )

    return response


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})