import pytest
from datetime import datetime

from rango_ja.domain.models import Order, Item, Refund, RefundReason
from rango_ja.domain.refund import calculate_refund
from rango_ja.domain.errors import ValueExceedsLimit, DuplicateRefund, OrderFromAnotherCustomer
from rango_ja.domain.authorization import ensure_owner
from rango_ja.config import get_settings

def create_mock_order(**kwargs):
    # Cria um pedido base, permitindo sobrescrever campos específicos
    base_data = dict(
        pedido_id="P9999",
        cliente_id="C01",
        restaurante="Teste",
        status="entregue",
        total=100.0,
        entregue_em=datetime.fromisoformat("2026-10-09T19:00:00"),
        previsto_para=datetime.fromisoformat("2026-10-09T18:00:00"),
        itens=[Item(nome="Refri", preco=10.0)],
        reembolsos=[]
    )
    base_data.update(kwargs)
    return Order(**base_data)

@pytest.fixture
def settings():
    # Pega as configurações e define a data fixa do desafio
    s = get_settings()
    s.reference_datetime = "2026-10-10T21:00:00-03:00"
    return s

def test_refund_delay_success(settings):
    order = create_mock_order()
    # Atraso de 1h > 30 min. Deve aprovar 20% de 100 = 20.0
    result = calculate_refund(order, RefundReason.DELAY, settings=settings)
    assert result.approved is True
    assert result.value == 20.0

def test_refund_limit_exceeded(settings):
    order = create_mock_order(total=300.0) # 20% de 300 = 60.0 (Acima do limite de 50)
    with pytest.raises(ValueExceedsLimit):
        calculate_refund(order, RefundReason.DELAY, settings=settings)

def test_refund_duplicate(settings):
    order = create_mock_order()
    order.reembolsos.append(Refund(valor=20.0, motivo="atraso", data=datetime.now()))
    with pytest.raises(DuplicateRefund):
        calculate_refund(order, RefundReason.DELAY, settings=settings)

def test_authorization_fail():
    order = create_mock_order()
    with pytest.raises(OrderFromAnotherCustomer):
        ensure_owner(order, "C02") # Pedido é do C01