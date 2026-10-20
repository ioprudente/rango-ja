import json
from datetime import datetime
from pathlib import Path

from rango_ja.actions.jsonfile import append_json_list, read_json_list
from rango_ja.config import get_settings
from rango_ja.domain.authorization import ensure_owner
from rango_ja.domain.errors import DomainError, OrderFromAnotherCustomer, OrderNotFound, ValueExceedsLimit
from rango_ja.domain.models import Refund, RefundReason
from rango_ja.domain.refund import calculate_refund
from rango_ja.domain.repository import get_repository
from rango_ja.tools.schemas import ConsultOrderArgs, EscalateToHumanArgs, ListOrdersArgs, RequestRefundArgs, SearchPoliciesArgs

ORDER_NOT_FOUND_MSG = "Não encontrei esse pedido na sua conta."
_REASON_ALIASES = {"cancelamento": "cancelamento_restaurante", "falta_de_item": "item_faltante"}

def brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _error(msg: str) -> str:
    return json.dumps({"erro": msg, "mensagem_cliente": msg}, ensure_ascii=False)

def _reference_iso() -> str:
    return datetime.fromisoformat(get_settings().reference_datetime).isoformat()

def _get_own_order(customer_id: str, order_id: str):
    repo = get_repository()
    try:
        order = repo.get(order_id)
        ensure_owner(order, customer_id)
    except (OrderNotFound, OrderFromAnotherCustomer):
        return None
    return order

def execute_consult_order(customer_id: str, args: ConsultOrderArgs) -> str:
    order = _get_own_order(customer_id, args.pedido_id)
    if order is None:
        return _error(ORDER_NOT_FOUND_MSG)
    return json.dumps({
        "status": "ok", "pedido_id": order.pedido_id, "restaurante": order.restaurante,
        "status_pedido": order.status, "itens": [{"nome": i.nome, "preco": i.preco} for i in order.itens],
        "taxa_entrega": order.taxa_entrega, "total": order.total,
        "previsto_para": order.previsto_para.isoformat() if order.previsto_para else None,
        "entregue_em": order.entregue_em.isoformat() if order.entregue_em else None,
        "cancelado_em": order.cancelado_em.isoformat() if order.cancelado_em else None, "tem_reembolso": order.has_refund(),
    }, ensure_ascii=False)

def execute_list_orders(customer_id: str, args: ListOrdersArgs) -> str:
    orders = get_repository().list_by_customer(customer_id)
    return json.dumps({"status": "ok", "pedidos": [{"pedido_id": o.pedido_id, "status_pedido": o.status, "total": o.total} for o in orders]}, ensure_ascii=False)

def execute_request_refund(customer_id: str, args: RequestRefundArgs) -> str:
    order = _get_own_order(customer_id, args.pedido_id)
    if order is None:
        return _error(ORDER_NOT_FOUND_MSG)

    try:
        reason = RefundReason(_REASON_ALIASES.get(args.motivo, args.motivo))
    except ValueError:
        return _error("Motivo inválido. Use 'atraso', 'item_faltante' ou 'cancelamento_restaurante'.")

    item_name = args.item if args.item and args.item != "nao_aplicavel" else None

    try:
        result = calculate_refund(order, reason, item_name)
    except ValueExceedsLimit as exc:
        esc = json.loads(execute_escalate_to_human(customer_id, EscalateToHumanArgs(pedido_id=order.pedido_id, motivo=f"Reembolso calculado de {brl(exc.value)} acima do limite automático ({reason.value}).")))
        return json.dumps({
            "status": "escalado", "valor_calculado": exc.value, "pedido_id": order.pedido_id,
            "escalacao": {"pedido_id": order.pedido_id, "motivo": esc.get("motivo"), "status": esc["status"]},
            "mensagem_cliente": f"O reembolso calculado para o pedido {order.pedido_id} é de {brl(exc.value)}, acima do limite de {brl(get_settings().max_refund_auto)} para aprovação automática. Encaminhei seu caso para um atendente humano, que fará a análise em até 24 horas.",
        }, ensure_ascii=False)
    except DomainError as exc:
        return _error(str(exc))

    if not result.approved:
        return _error("Não há atraso suficiente: a entrega ocorreu dentro de 30 minutos do horário previsto.")

    order.reembolsos.append(Refund(valor=result.value, motivo=result.reason.value, data=datetime.fromisoformat(get_settings().reference_datetime)))
    get_repository().update(order)
    return json.dumps({
        "status": "aprovado", "valor": result.value, "pedido_id": order.pedido_id,
        "mensagem_cliente": f"Reembolso de {brl(result.value)} aprovado para o pedido {order.pedido_id}. O valor volta para o mesmo meio de pagamento (Pix: até 2 dias úteis; cartão de crédito: até duas faturas).",
    }, ensure_ascii=False)

def execute_escalate_to_human(customer_id: str, args: EscalateToHumanArgs) -> str:
    if args.pedido_id and _get_own_order(customer_id, args.pedido_id) is None:
        return _error(ORDER_NOT_FOUND_MSG)

    path = get_settings().escalations_path
    if args.pedido_id and any(e["cliente_id"] == customer_id and e.get("pedido_id") == args.pedido_id for e in read_json_list(path)):
        return json.dumps({"status": "ja_escalado", "motivo": args.motivo, "mensagem_cliente": "Seu caso já foi encaminhado para um atendente humano, que responderá em até 24 horas."}, ensure_ascii=False)

    append_json_list(path, {"cliente_id": customer_id, "pedido_id": args.pedido_id or None, "motivo": args.motivo, "data": _reference_iso()})
    return json.dumps({"status": "ok", "motivo": args.motivo, "mensagem_cliente": "Encaminhei seu caso para um atendente humano, que responderá em até 24 horas."}, ensure_ascii=False)

def execute_search_policies(customer_id: str, args: SearchPoliciesArgs) -> str:
    content = Path(get_settings().politicas_path).read_text(encoding="utf-8")
    sections = content.split("\n## ")
    stopwords = {"o", "a", "os", "as", "de", "do", "da", "em", "um", "uma", "que", "e", "para", "com", "se", "meu", "no", "na", "quanto", "tempo"}
    words = {w.lower().strip("?.,!") for w in args.pergunta.split()}
    words = {w for w in words if w not in stopwords and len(w) > 2}

    best, best_hits = "", 0
    for section in sections:
        hits = sum(1 for w in words if w in section.lower())
        if hits > best_hits:
            best, best_hits = section, hits
    if not best:
        return _error("Não encontrei essa informação nas políticas de atendimento.")
    return json.dumps({"status": "ok", "trecho_relevante": best.strip(), "instrucao": "Responda usando APENAS este trecho; não invente regras."}, ensure_ascii=False)
