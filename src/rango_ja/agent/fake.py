from rango_ja.schemas import ChatResponse, ToolCall


class FakeOrchestrator:
    """Orquestrador de desenvolvimento: não chama LLM. Substitua depois."""

    async def handle(
        self, *, cliente_id: str, session_id: str, mensagem: str
    ) -> ChatResponse:
        return ChatResponse(
            resposta=(
                f"[fake] Recebi sua mensagem, {cliente_id}. "
                f"Ainda não há LLM conectado."
            ),
            acoes=[
                ToolCall(
                    ferramenta="consultar_pedido",
                    argumentos={"pedido_id": "P1001"},
                    resultado="ok",
                )
            ],
        )