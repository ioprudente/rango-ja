import json

from rango_ja.tools import TOOLS_MAP
from rango_ja.tools.schemas import (
    ConsultOrderArgs,
    RequestRefundArgs,
    SearchPoliciesArgs,
)
from rango_ja.domain.models import RefundReason

def run_scenario(number, customer, message, tool_name, args_obj):
    print(f"\n{'-'*60}")
    print(f"CENÁRIO {number} | Cliente: {customer}")
    print(f"Mensagem: \"{message}\"")
    print(f"Ação do 'LLM': Chamar ferramenta '{tool_name}'")
    print(f"Argumentos enviados: {args_obj.model_dump()}")
    
    # Executa a SUA ferramenta (passando o cliente logado e os argumentos)
    tool_def = TOOLS_MAP.get(tool_name)
    if not tool_def:
        print("ERRO: Ferramenta não encontrada!")
        return

    resultado_json = tool_def.func(customer, args_obj)
    print(f"Resultado da sua API/Tool:")
    
    try:
        parsed = json.loads(resultado_json)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(resultado_json)

if __name__ == "__main__":
    print("Iniciando Teste Ponta a Ponta (E2E) - 6 Cenários do PDF\n")

    # Cenário 1: Atraso (Reembolso automático 17.98)
    run_scenario(
        1, "C01", "Meu pedido P1001 atrasou muito, quero meu dinheiro de volta",
        "solicitar_reembolso",
        RequestRefundArgs(pedido_id="P1001", motivo=RefundReason.DELAY)
    )

    # Cenário 2: Item Faltante (Reembolso automático 8.00)
    run_scenario(
        2, "C01", "Faltou o refrigerante no P1002",
        "solicitar_reembolso",
        RequestRefundArgs(pedido_id="P1002", motivo=RefundReason.MISSING_ITEM, item="Refrigerante lata")
    )

    # Cenário 3: Consulta de status (Nenhuma ação)
    run_scenario(
        3, "C02", "Onde está meu pedido P1003?",
        "consultar_pedido",
        ConsultOrderArgs(pedido_id="P1003")
    )

    # Cenário 4: Cancelamento (R$ 120 - excede limite, deve dar erro pedindo escalonamento)
    run_scenario(
        4, "C02", "O restaurante cancelou o P1004, quero o reembolso",
        "solicitar_reembolso",
        RequestRefundArgs(pedido_id="P1004", motivo=RefundReason.RESTAURANT_CANCELLATION)
    )

    # Cenário 5: Dúvida de política (RAG)
    run_scenario(
        5, "C01", "Em quanto tempo o dinheiro volta no Pix?",
        "buscar_politicas",
        SearchPoliciesArgs(pergunta="Em quanto tempo o dinheiro volta no Pix?")
    )

    # Cenário 6: Privacidade (Cliente C03 tentando ver pedido do C01)
    run_scenario(
        6, "C03", "Quero saber do pedido P1001",
        "consultar_pedido",
        ConsultOrderArgs(pedido_id="P1001")
    )
    print(f"\n{'-'*60}")
    print("Fim dos testes.\n")
