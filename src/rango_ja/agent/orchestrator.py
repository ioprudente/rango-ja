import json
import logging
import asyncio
import httpx

from rango_ja.config import get_settings
from rango_ja.memory.base import MemoryStore
from rango_ja.schemas import ChatResponse, ToolCall
from rango_ja.tools import TOOLS_MAP

logger = logging.getLogger(__name__)

class OllamaOrchestrator:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store
        self.settings = get_settings()
        
        # URL local padrão do Ollama
        self.api_url = "http://localhost:11434/api/chat"
        
        # Prepara as ferramentas no formato OpenAI/Ollama
        self.tools_schema = []
        for name, tool_def in TOOLS_MAP.items():
            # Limpa o schema de parâmetros para o formato padrão
            params = tool_def.gemini_parameters.copy()
            if not params.get("properties"):
                params.pop("properties", None)
                params.pop("required", None)
                
            self.tools_schema.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_def.description,
                    "parameters": params
                }
            })

    async def handle(
        self, *, cliente_id: str, session_id: str, mensagem: str
    ) -> ChatResponse:
        history = await self.memory.get_history(session_id)
        
        messages = []

        system_prompt = (
            "Você é o assistente virtual da Rango Já. "
            f"O cliente logado é o ID '{cliente_id}'. "
            "Seja educado, direto e resolva o problema do cliente usando as ferramentas. "
            "Se o cliente reclamar de atraso, item faltante ou cancelamento, use 'solicitar_reembolso'. "
            "Se a ferramenta retornar um erro de limite, use 'escalar_para_humano'. "
            "Para dúvidas sobre regras (ex: Pix), use 'buscar_politicas'. "
            "Escreva uma resposta final amigável e natural para o cliente."
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
                    "options": {"temperature": 0.0}
                }
                
                data = None
                for attempt in range(3):
                    try:
                        logger.info(f"Chamando Ollama (Tentativa {attempt+1})...")
                        response = await client.post(self.api_url, json=payload)
                        
                        # --- TRATAMENTO DE RATE LIMIT (429) ---
                        if response.status_code == 429:
                            logger.warning("Rate limit (429) do Ollama atingido. Aguardando backoff exponencial...")
                            await asyncio.sleep(2 ** attempt) 
                            continue
                            
                        # Levanta exceção para outros erros HTTP (4xx, 5xx)
                        response.raise_for_status()
                        
                        data = response.json()
                        break # Sucesso, sai do loop de retry
                        
                    except httpx.ReadTimeout:
                        logger.warning(f"Timeout na tentativa {attempt + 1}.")
                        await asyncio.sleep(1)
                    except httpx.HTTPStatusError as exc:
                        logger.error(f"Erro HTTP no Ollama: {exc.response.status_code} - {exc.response.text}")
                        await asyncio.sleep(1)
                    except Exception as exc:
                        logger.error(f"Erro inesperado na comunicação com Ollama: {exc}")
                        await asyncio.sleep(1)
                
                if not data:
                    return ChatResponse(
                        resposta="O sistema está um pouco sobrecarregado agora. Poderia tentar novamente em alguns instantes?",
                        acoes=executions
                    )

                message = data.get("message", {})
                tool_calls = message.get("tool_calls", [])
                
                # Se não houver chamada de ferramenta, é a resposta final
                if not tool_calls:
                    resposta_texto = message.get("content", resposta_texto)
                    break
                
                # Adiciona a resposta da IA (com as chamadas de ferramenta) no histórico
                messages.append(message)
                
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name")
                    tool_args = func.get("arguments", {})
                    
                    # O Ollama às vezes retorna os argumentos como string JSON
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}
                            
                    tool_def = TOOLS_MAP.get(tool_name)
                    
                    if not tool_def:
                        result_str = json.dumps({"erro": "Ferramenta desconhecida"})
                        executions.append(ToolCall(ferramenta=tool_name, argumentos=tool_args, resultado="erro"))
                    else:
                        try:
                            # Validação Pydantic rigorosa dos argumentos gerados pelo LLM
                            args = tool_def.args_schema(**tool_args)
                            result_str = tool_def.func(cliente_id, args)
                            
                            executions.append(
                                ToolCall(
                                    ferramenta=tool_name,
                                    argumentos=tool_args,
                                    resultado="ok" if "erro" not in result_str else "erro"
                                )
                            )
                        except Exception as e:
                            logger.error(f"Erro ao executar a ferramenta {tool_name}: {e}")
                            result_str = json.dumps({"erro": str(e)})
                            executions.append(ToolCall(ferramenta=tool_name, argumentos=tool_args, resultado="erro"))

                    # Devolve o resultado da ferramenta para o Ollama
                    messages.append({
                        "role": "tool",
                        "content": result_str,
                        "name": tool_name
                    })

        return ChatResponse(resposta=resposta_texto, acoes=executions)