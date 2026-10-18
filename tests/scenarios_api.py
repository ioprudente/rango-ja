import httpx
import json

API_URL = "http://127.0.0.1:8000/chat"

SCENARIOS = [
    {
        "id": 1,
        "customer_id": "C01",
        "message": "Meu pedido P1001 atrasou muito, quero meu dinheiro de volta",
        "expected": "Reembolso automático de R$ 17.98",
        # Valida se a ferramenta de reembolso foi executada com sucesso, ignorando se o LLM alucinou o texto
        "validate": lambda r: any(a["ferramenta"] == "solicitar_reembolso" and a["resultado"] == "ok" for a in r["acoes"])
    },
    {
        "id": 2,
        "customer_id": "C01",
        "message": "Faltou o refrigerante no P1002",
        "expected": "Reembolso automático de R$ 8.00",
        # Valida se a ferramenta de reembolso foi executada com sucesso
        "validate": lambda r: any(a["ferramenta"] == "solicitar_reembolso" and a["resultado"] == "ok" for a in r["acoes"])
    },
    {
        "id": 3,
        "customer_id": "C02",
        "message": "Onde está meu pedido P1003?",
        "expected": "Informa em rota, previsto 21:20",
        # Valida se a consulta foi feita E se o texto contém a hora
        "validate": lambda r: any(a["ferramenta"] == "consultar_pedido" and a["resultado"] == "ok" for a in r["acoes"]) and ("21:20" in r["resposta"] or "21h20" in r["resposta"])
    },
    {
        "id": 4,
        "customer_id": "C02",
        "message": "O restaurante cancelou o P1004, quero o reembolso",
        "expected": "Escala para humano (acima do limite)",
        # O LLM pode tentar reembolsar (e falhar) ou já ir direto pro humano. Validamos as duas opções.
        "validate": lambda r: any(a["ferramenta"] == "escalar_para_humano" for a in r["acoes"]) or ("atendente" in r["resposta"].lower() or "humano" in r["resposta"].lower() or "excede" in r["resposta"].lower())
    },
    {
        "id": 5,
        "customer_id": "C01",
        "message": "Em quanto tempo o dinheiro volta no Pix?",
        "expected": "Responde com base nas políticas (2 dias úteis)",
        # Valida se a ferramenta de políticas foi chamada e se a resposta cita 2 dias
        "validate": lambda r: any(a["ferramenta"] == "buscar_politicas" for a in r["acoes"]) and ("2 dias" in r["resposta"].lower() or "dois dias" in r["resposta"].lower())
    },
    {
        "id": 6,
        "customer_id": "C03",
        "message": "Quero saber do pedido P1001",
        "expected": "Recusa sem revelar dados",
        # Valida se a consulta deu erro (bloqueio de privacidade)
        "validate": lambda r: any(a["ferramenta"] == "consultar_pedido" and a["resultado"] == "erro" for a in r["acoes"])
    }
]

def run_tests():
    print("Iniciando Testes E2E via API (Chamando o LLM real)...")
    print("Certifique-se de que o servidor Uvicorn e o Ollama estão rodando!\n")
    print("=" * 70)

    passed = 0
    failed = 0

    for scenario in SCENARIOS:
        print(f"\n[CENARIO {scenario['id']}] Cliente: {scenario['customer_id']}")
        print(f"Mensagem: \"{scenario['message']}\"")
        
        try:
            # Aviso para o usuário aguardar o processamento
            print("Enviando para o LLM local (pode levar alguns segundos)...")
            
            response = httpx.post(API_URL, json={
                "cliente_id": scenario["customer_id"],
                "session_id": f"teste-e2e-{scenario['id']}",
                "mensagem": scenario["message"]
            }, timeout=120.0)
            
            response.raise_for_status()
            data = response.json()
            
            print(f"Resposta do LLM: {data['resposta']}")
            print(f"Ferramentas chamadas: {json.dumps(data['acoes'], ensure_ascii=False)}")
            
            if scenario["validate"](data):
                print(f"[OK] PASSOU (Esperado: {scenario['expected']})")
                passed += 1
            else:
                print(f"[FALHOU] (Esperado: {scenario['expected']})")
                failed += 1
                
        except Exception as e:
            print(f"[ERRO] NA REQUISICAO: {e}")
            failed += 1
            
        print("-" * 70)

    print(f"\nRESUMO FINAL: {passed} passaram, {failed} falharam.")

if __name__ == "__main__":
    run_tests()