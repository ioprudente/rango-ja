import json
from datetime import datetime
from pathlib import Path

from rango_ja.config import get_settings
from rango_ja.domain.authorization import ensure_owner
from rango_ja.domain.errors import (
    DomainError,
    ClaimOutOfTimeframe,
    ItemNotFoundInOrder,
    UnsupportedReason,
    OrderFromAnotherCustomer,
    OrderNotFound,
    DuplicateRefund,
    ValueExceedsLimit,
)
from rango_ja.domain.models import Refund
from rango_ja.domain.refund import calculate_refund
from rango_ja.domain.repository import get_repository
from rango_ja.tools.schemas import (
    SearchPoliciesArgs,
    ConsultOrderArgs,
    EscalateToHumanArgs,
    ListOrdersArgs,
    RequestRefundArgs,
)


def _format_error(msg: str) -> str:
    return json.dumps({"erro": msg}, ensure_ascii=False)


def execute_consult_order(customer_id: str, args: ConsultOrderArgs) -> str:
    repo = get_repository()
    try:
        order = repo.get(args.pedido_id)
        ensure_owner(order, customer_id)
    except (OrderNotFound, OrderFromAnotherCustomer):
        return _format_error("Pedido não encontrado ou não pertence a você.")

    data = {
        "pedido_id": order.pedido_id,
        "restaurante": order.restaurante,
        "status": order.status,
        "itens": [{"nome": i.nome, "preco": i.preco} for i in order.itens],
        "total": order.total,
        "previsto_para": order.previsto_para.isoformat() if order.previsto_para else None,
        "entregue_em": order.entregue_em.isoformat() if order.entregue_em else None,
        "cancelado_em": order.cancelado_em.isoformat() if order.cancelado_em else None,
        "tem_reembolso": order.has_refund(),
    }
    return json.dumps(data, ensure_ascii=False)


def execute_list_orders(customer_id: str, args: ListOrdersArgs) -> str:
    repo = get_repository()
    orders = repo.list_by_customer(customer_id)
    summary = [
        {
            "pedido_id": o.pedido_id,
            "status": o.status,
            "total": o.total,
            "data": (o.entregue_em or o.previsto_para or o.cancelado_em).isoformat()
            if (o.entregue_em or o.previsto_para or o.cancelado_em) else None,
        }
        for o in orders
    ]
    return json.dumps(summary, ensure_ascii=False)


def execute_request_refund(customer_id: str, args: RequestRefundArgs) -> str:
    repo = get_repository()
    try:
        order = repo.get(args.pedido_id)
        ensure_owner(order, customer_id)
    except (OrderNotFound, OrderFromAnotherCustomer):
        return _format_error("Pedido não encontrado ou não pertence a você.")

    try:
        result = calculate_refund(
            order=order,
            reason=args.motivo,
            item_name=args.item,
        )
    except ValueExceedsLimit as e:
        return _format_error(
            f"O valor do reembolso é R$ {e.value:.2f}, o que excede o limite "
            f"automático de R$ {e.limit:.2f}. O caso precisa ser escalado para um atendente humano."
        )
    except ClaimOutOfTimeframe as e:
        return _format_error(str(e))
    except DuplicateRefund as e:
        return _format_error(str(e))
    except (ItemNotFoundInOrder, UnsupportedReason) as e:
        return _format_error(str(e))
    except DomainError as e:
        return _format_error(str(e))

    if not result.approved:
        return _format_error("Não há atraso suficiente para gerar reembolso.")

    new_refund = Refund(
        valor=result.value,
        motivo=result.reason.value,
        data=datetime.fromisoformat(get_settings().reference_datetime)
    )
    order.reembolsos.append(new_refund)
    repo.update(order)

    return json.dumps({
        "status": "aprovado",
        "valor": result.value,
        "mensagem": f"Reembolso de R$ {result.value:.2f} aprovado com sucesso."
    }, ensure_ascii=False)


def execute_escalate_to_human(customer_id: str, args: EscalateToHumanArgs) -> str:
    return json.dumps({
        "status": "escalado",
        "mensagem": f"Caso escalado para atendimento humano. Motivo: {args.motivo}"
    }, ensure_ascii=False)


def execute_search_policies(customer_id: str, args: SearchPoliciesArgs) -> str:
    settings = get_settings()
    path = Path(settings.politicas_path)
    
    if not path.exists():
        return _format_error("Documento de políticas não encontrado no sistema.")

    with path.open("r", encoding="utf-8") as f:
        content = f.read()

    return json.dumps({
        "politicas_completas": content,
        "instrucao": "Responda à pergunta do cliente usando APENAS as informações acima. Se não estiver lá, diga que não sabe."
    }, ensure_ascii=False)
