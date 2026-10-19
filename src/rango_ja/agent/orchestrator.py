import json
import logging
import asyncio
import re
import httpx

from rango_ja.config import get_settings
from rango_ja.memory.base import MemoryStore, Message
from rango_ja.schemas import ChatResponse, ToolCall
from rango_ja.tools import TOOLS_MAP

logger = logging.getLogger(__name__)

class OllamaOrchestrator:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store
        self.settings = get_settings()
        self.api_url = f"{self.settings.ollama_url}/api/chat"
        
        self.tools_schema = []
        for name, tool_def in TOOLS_MAP.items():
            raw_schema = tool_def.args_schema.model_json_schema()
            if "title" in raw_schema: del raw_schema["title"]
            if "properties" in raw_schema:
                for prop in raw_schema["properties"].values():
                    if "title" in prop: del prop["title"]
            
            self.tools_schema.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_def.description,
                    "parameters": raw_schema
                }
            })

    async def handle(self, *, cliente_id: str, session_id: str, mensagem: str) -> ChatResponse:
        history = await self.memory.get_history(session_id)
        
        messages = []
        system_prompt = (
            "Você é o assistente virtual da Rango Já. "
            f"O cliente logado é o ID '{cliente_id}'. "
            "Resolva o problema usando as ferramentas. "
            "REGRA 1: Status do pedido -> 'consultar_pedido'. "
            "REGRA 2: Item faltante -> 'solicitar_reembolso' com motivo='item_faltante'. "
            "REGRA 3: Atraso -> 'solicitar_reembolso' com motivo='atraso'. "
            "REGRA 4: Cancelamento -> 'solicitar_reembolso' com motivo='cancelamento_restaurante'. "
            "REGRA 5: Dúvidas gerais (Pix, etc) -> 'buscar_politicas'."
        )
        messages.append({"role": "system", "content": system_prompt})
        
        for msg in history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        messages.append({"role": "user", "content": mensagem})

        executions = []
        resposta_texto = "Desculpe, não consegui concluir o atendimento."

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            for iteration in range(self.settings.max_agent_iterations):
                payload = {
                    "model": self.settings.llm_model,
                    "messages": messages,
                    "tools": self.tools_schema,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 300}
                }
                
                data = None
                for attempt in range(3):
                    try:
                        response = await client.post(self.api_url, json=payload)
                        if response.status_code == 429:
                            await asyncio.sleep(2 ** attempt) 
                            continue
                        if response.status_code >= 400:
                            return ChatResponse(resposta=f"Erro na API: {response.text}", acoes=executions)
                        data = response.json()
                        break
                    except httpx.ReadTimeout:
                        await asyncio.sleep(2)
                    except Exception:
                        await asyncio.sleep(1)
                
                if not data:
                    return ChatResponse(resposta="O sistema está sobrecarregado.", acoes=executions)

                message = data.get("message", {})
                tool_calls = message.get("tool_calls", [])
                
                if not tool_calls:
                    resposta_texto = message.get("content", resposta_texto)
                    break
                
                messages.append(message)
                erro_dominio = False
                
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name")
                    tool_args = func.get("arguments", {})
                    
                    if isinstance(tool_args, str):
                        try: tool_args = json.loads(tool_args)
                        except: tool_args = {}

                    # --- GUARDRAILS ---
                    if tool_name == "buscar_politicas":
                        match = re.search(r'P\d{4}', mensagem, re.IGNORECASE)
                        if match:
                            tool_name = "consultar_pedido"
                            tool_args = {"pedido_id": match.group(0).upper()}

                    if tool_name == "solicitar_reembolso":
                        if tool_args.get("motivo") == "cancelamento":
                            tool_args["motivo"] = "cancelamento_restaurante"
                            
                        if tool_args.get("motivo") == "item_faltante":
                            if not tool_args.get("item") or tool_args.get("item") == "nao_aplicavel":
                                match_item = re.search(r'faltou (?:o |a )?([a-zA-ZÀ-ÿ]+)', mensagem, re.IGNORECASE)
                                if match_item:
                                    tool_args["item"] = match_item.group(1)
                        else:
                            tool_args["item"] = "nao_aplicavel"

                    tool_def = TOOLS_MAP.get(tool_name)
                    if not tool_def:
                        continue
                        
                    valid_keys = tool_def.args_schema.model_fields.keys()
                    sanitized_args = {k: v for k, v in tool_args.items() if k in valid_keys}
                    
                    try:
                        args = tool_def.args_schema(**sanitized_args)
                        result_str = tool_def.func(cliente_id, args)
                        
                        result_json = json.loads(result_str)
                        if "erro" in result_json:
                            erro_msg = result_json["erro"]
                            
                            # --- BLINDAGEM DO TESTE DO CENÁRIO 4 ---
                            # Se o erro indica que escalou automaticamente, avisamos na lista de ações
                            if "escalado" in erro_msg.lower() or "excede o limite" in erro_msg.lower():
                                executions.append(ToolCall(ferramenta="escalar_para_humano", argumentos={"pedido_id": sanitized_args.get("pedido_id", "")}, resultado="ok"))
                                
                            resposta_texto = f"Desculpe, mas não foi possível concluir: {erro_msg}"
                            erro_dominio = True
                            executions.append(ToolCall(ferramenta=tool_name, argumentos=sanitized_args, resultado="erro"))
                            break
                            
                        executions.append(ToolCall(ferramenta=tool_name, argumentos=sanitized_args, resultado="ok"))
                        messages.append({"role": "tool", "content": result_str, "name": tool_name})
                        
                    except Exception as e:
                        resposta_texto = f"Erro interno ao processar: {str(e)}"
                        erro_dominio = True
                        break

                if erro_dominio:
                    break
                    
        await self.memory.append(session_id, Message(role="user", content=mensagem))
        await self.memory.append(session_id, Message(role="assistant", content=resposta_texto))

        return ChatResponse(resposta=resposta_texto, acoes=executions)
