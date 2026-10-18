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
        gemini_parameters: dict,
    ) -> None:
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.func = func
        self.gemini_parameters = gemini_parameters


TOOLS_MAP: dict[str, ToolDefinition] = {
    "consultar_pedido": ToolDefinition(
        name="consultar_pedido",
        description="Retorna status, itens, valores e horários de um pedido específico do cliente logado.",
        args_schema=ConsultOrderArgs,
        func=implementations.execute_consult_order,
        gemini_parameters={
            "type": "OBJECT",
            "properties": {
                "pedido_id": {"type": "STRING", "description": "ID do pedido (ex: P1001)"}
            },
            "required": ["pedido_id"]
        }
    ),
    "listar_pedidos": ToolDefinition(
        name="listar_pedidos",
        description="Lista os pedidos recentes do cliente logado.",
        args_schema=ListOrdersArgs,
        func=implementations.execute_list_orders,
        gemini_parameters={
            "type": "OBJECT",
            "properties": {}
        }
    ),
    "buscar_politicas": ToolDefinition(
        name="buscar_politicas",
        description="Recupera os trechos relevantes das políticas de atendimento.",
        args_schema=SearchPoliciesArgs,
        func=implementations.execute_search_policies,
        gemini_parameters={
            "type": "OBJECT",
            "properties": {
                "pergunta": {"type": "STRING", "description": "Dúvida do cliente sobre as políticas"}
            },
            "required": ["pergunta"]
        }
    ),
    "solicitar_reembolso": ToolDefinition(
        name="solicitar_reembolso",
        description="Calcula e registra um reembolso se as regras permitirem.",
        args_schema=RequestRefundArgs,
        func=implementations.execute_request_refund,
        gemini_parameters={
            "type": "OBJECT",
            "properties": {
                "pedido_id": {"type": "STRING", "description": "ID do pedido"},
                "motivo": {"type": "STRING", "description": "Motivo. Valores permitidos: 'atraso', 'item_faltante', 'cancelamento_restaurante'."},
                "item": {"type": "STRING", "description": "Nome do item (se faltante)"}
            },
            "required": ["pedido_id", "motivo"]
        }
    ),
    "escalar_para_humano": ToolDefinition(
        name="escalar_para_humano",
        description="Registra um encaminhamento para um atendente humano.",
        args_schema=EscalateToHumanArgs,
        func=implementations.execute_escalate_to_human,
        gemini_parameters={
            "type": "OBJECT",
            "properties": {
                "pedido_id": {"type": "STRING", "description": "ID do pedido, se aplicável"},
                "motivo": {"type": "STRING", "description": "Motivo do escalonamento"}
            },
            "required": ["motivo"]
        }
    ),
}

def get_tool_schemas() -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "parameters": t.gemini_parameters}
        for t in TOOLS_MAP.values()
    ]
