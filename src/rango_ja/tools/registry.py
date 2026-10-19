from typing import Callable, Type
from pydantic import BaseModel
from rango_ja.tools import implementations
from rango_ja.tools.schemas import *

class ToolDefinition:
    def __init__(self, name: str, description: str, args_schema: Type[BaseModel], func: Callable):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.func = func

TOOLS_MAP = {
    "consultar_pedido": ToolDefinition("consultar_pedido", "Consulta status do pedido", ConsultOrderArgs, implementations.execute_consult_order),
    "listar_pedidos": ToolDefinition("listar_pedidos", "Lista pedidos", ListOrdersArgs, implementations.execute_list_orders),
    "buscar_politicas": ToolDefinition("buscar_politicas", "Busca regras", SearchPoliciesArgs, implementations.execute_search_policies),
    "solicitar_reembolso": ToolDefinition("solicitar_reembolso", "Pede reembolso", RequestRefundArgs, implementations.execute_request_refund),
    "escalar_para_humano": ToolDefinition("escalar_para_humano", "Chama humano", EscalateToHumanArgs, implementations.execute_escalate_to_human),
}
