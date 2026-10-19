import json
from datetime import datetime
from pathlib import Path
from rango_ja.config import get_settings
from rango_ja.domain.authorization import ensure_owner
from rango_ja.domain.errors import *
from rango_ja.domain.models import Refund, RefundReason
from rango_ja.domain.refund import calculate_refund
from rango_ja.domain.repository import get_repository
from rango_ja.tools.schemas import *

def _format_error(msg: str) -> str: return json.dumps({"erro": msg}, ensure_ascii=False)

def execute_consult_order(customer_id: str, args: ConsultOrderArgs) -> str:
    repo = get_repository()
    try:
        order = repo.get(args.pedido_id)
        ensure_owner(order, customer_id)
    except (OrderNotFound, OrderFromAnotherCustomer):
        return _format_error("Pedido não encontrado ou não pertence a você.")
    
    # CORREÇÃO: Retorna todos os dados exigidos (itens, taxa, horários)
    return json.dumps({
        "pedido_id": order.pedido_id,
        "restaurante": order.restaurante,
        "status": order.status,
        "itens": [{"nome": i.nome, "preco": i.preco} for i in order.itens],
        "taxa_entrega": order.taxa_entrega,
        "total": order.total,
        "previsto_para": order.previsto_para.isoformat() if order.previsto_para else None,
        "entregue_em": order.entregue_em.isoformat() if order.entregue_em else None
    }, ensure_ascii=False)

def execute_list_orders(customer_id: str, args: ListOrdersArgs) -> str:
    orders = get_repository().list_by_customer(customer_id)
    return json.dumps([{"pedido_id": o.pedido_id, "status": o.status} for o in orders])

def execute_request_refund(customer_id: str, args: RequestRefundArgs) -> str:
    repo = get_repository()
    try:
        order = repo.get(args.pedido_id)
        ensure_owner(order, customer_id)
    except (OrderNotFound, OrderFromAnotherCustomer):
        return _format_error("Pedido não encontrado ou não pertence a você.")
    
    try:
        # CORREÇÃO: Captura o ValueError caso o LLM invente um motivo inválido
        try:
            reason = RefundReason(args.motivo)
        except ValueError:
            return _format_error(f"Motivo '{args.motivo}' inválido. Use 'atraso', 'item_faltante' ou 'cancelamento_restaurante'.")
            
        item_name = args.item if args.item and args.item != "nao_aplicavel" else None
        result = calculate_refund(order, reason, item_name)
    except ValueExceedsLimit as e:
        motivo_escala = f"Reembolso de R$ {e.value:.2f} excede o limite. O caso foi escalado automaticamente."
        execute_escalate_to_human(customer_id, EscalateToHumanArgs(pedido_id=args.pedido_id, motivo=motivo_escala))
        # CORREÇÃO: Adiciona o prazo de 24h exigido pelo cenário 4
        return _format_error(f"O valor excede o limite de R$ 50,00. O caso foi escalado automaticamente para um atendente humano, que responderá em até 24 horas.")
    except DomainError as e:
        return _format_error(str(e))
        
    if not result.approved: return _format_error("Não há atraso suficiente.")
    
    order.reembolsos.append(Refund(valor=result.value, motivo=result.reason.value, data=datetime.fromisoformat(get_settings().reference_datetime)))
    repo.update(order)
    return json.dumps({"status": "aprovado", "valor": result.value}, ensure_ascii=False)

def execute_escalate_to_human(customer_id: str, args: EscalateToHumanArgs) -> str:
    repo = get_repository()
    # CORREÇÃO: Valida se o pedido pertence ao cliente antes de escalar
    if args.pedido_id:
        try:
            order = repo.get(args.pedido_id)
            ensure_owner(order, customer_id)
        except (OrderNotFound, OrderFromAnotherCustomer):
            return _format_error("Pedido não encontrado ou não pertence a você.")

    log_path = Path("data/escalations.json")
    log_path.parent.mkdir(exist_ok=True)
    escalations = []
    if log_path.exists():
        escalations = json.loads(log_path.read_text(encoding="utf-8"))
    
    escalations.append({
        "cliente_id": customer_id,
        "pedido_id": args.pedido_id,
        "motivo": args.motivo,
        "data": datetime.fromisoformat(get_settings().reference_datetime).isoformat()
    })
    log_path.write_text(json.dumps(escalations, indent=2, ensure_ascii=False), encoding="utf-8")
    return json.dumps({"status": "escalado", "mensagem": "Encaminhado para humano com sucesso."})

def execute_search_policies(customer_id: str, args: SearchPoliciesArgs) -> str:
    content = Path(get_settings().politicas_path).read_text(encoding="utf-8")
    sections = content.split("##")
    
    # CORREÇÃO: Melhora o RAG com pontuação por palavras-chave
    best_match = ""
    max_hits = 0
    # Remove palavras comuns (stopwords simples)
    stopwords = {"o", "a", "os", "as", "de", "do", "da", "em", "um", "uma", "que", "e", "para", "com", "se", "meu"}
    query_words = set(w.lower() for w in args.pergunta.replace("?", "").split() if w.lower() not in stopwords and len(w) > 2)
    
    for section in sections:
        hits = sum(1 for word in query_words if word in section.lower())
        if hits > max_hits:
            max_hits = hits
            best_match = section

    if not best_match or max_hits == 0:
        return _format_error("Política não encontrada para a sua dúvida.")

    return json.dumps({"trecho_relevante": f"##{best_match.strip()}"}, ensure_ascii=False)
