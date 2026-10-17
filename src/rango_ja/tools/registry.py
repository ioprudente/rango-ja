from typing import Callable, Type
from pydantic import BaseModel

from rango_ja.tools import implementations
from rango_ja.tools.schemas import (
    SearchPoliciesArgs,
    ConsultOrderArgs,
    EscalateToHumanArgs,
    ListOrdersArgs,
    RequestRefundArgs,
)


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        args_schema: Type[BaseModel],
        func: Callable[[str, BaseModel], str],
    ) -> None:
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.func = func

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            },
        }


TOOLS_MAP: dict[str, ToolDefinition] = {
    "consultar_pedido": ToolDefinition(
        name="consultar_pedido",
        description="Retorna status, itens, valores e horários de um pedido específico do cliente logado.",
        args_schema=ConsultOrderArgs,
        func=implementations.execute_consult_order,
    ),
    "listar_pedidos": ToolDefinition(
        name="listar_pedidos",
        description="Lista os pedidos recentes do cliente logado.",
        args_schema=ListOrdersArgs,
        func=implementations.execute_list_orders,
    ),
    "buscar_politicas": ToolDefinition(
        name="buscar_politicas",
        description="Recupera os trechos relevantes das políticas de atendimento. Use para responder dúvidas gerais (prazos, reembolsos, horários).",
        args_schema=SearchPoliciesArgs,
        func=implementations.execute_search_policies,
    ),
    "solicitar_reembolso": ToolDefinition(
        name="solicitar_reembolso",
        description="Calcula e registra um reembolso se as regras permitirem. Não passe o valor, o sistema calcula automaticamente.",
        args_schema=RequestRefundArgs,
        func=implementations.execute_request_refund,
    ),
    "escalar_para_humano": ToolDefinition(
        name="escalar_para_humano",
        description="Registra um encaminhamento para um atendente humano quando o problema não pode ser resolvido automaticamente.",
        args_schema=EscalateToHumanArgs,
        func=implementations.execute_escalate_to_human,
    ),
}


def get_tool_schemas_for_openai() -> list[dict]:
    return [tool.to_openai_schema() for tool in TOOLS_MAP.values()]
