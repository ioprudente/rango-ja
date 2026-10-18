import httpx
import json

URL = "http://127.0.0.1:8000/chat"

cenarios = [
    {
        "cliente_id": "C01",
        "session_id": "e2e-1",
        "mensagem": "Meu pedido P1001 atrasou muito, quero meu dinheiro de volta",
        "esperado": "Reembolso de R$ 17.98"
    },
    {
        "cliente_id": "C03",
        "session_id": "e2e-2",
        "mensagem": "Quero saber do pedido P1001",
        "esperado": "Recusa de privacidade"
    }
]

print("Iniciando Testes E2E via API (Chamando o LLM real)...\n")
print("Certifique-se de que o servidor Uvicorn e o Ollama estão rodando!\n")

for i, c in enumerate(cenarios, 1):
    print(f"--- Cenário {i} ---")
    print(f"Mensagem: {c['mensagem']}")
    try:
        resp = httpx.post(URL, json={
            "cliente_id": c["cliente_id"],
            "session_id": c["session_id"],
            "mensagem": c["mensagem"]
        }, timeout=120.0)
        resp.raise_for_status()
        
        dados = resp.json()
        print(f"Resposta do LLM: {dados['resposta']}")
        print(f"Ações executadas: {json.dumps(dados['acoes'], indent=2)}")
        print(f"Esperado: {c['esperado']}\n")
        
    except Exception as e:
        print(f"Erro ao chamar API: {e}\n")
