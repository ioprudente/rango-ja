class DomainError(Exception):
    """Erro de domínio. Sempre tratado pelo código, nunca pelo LLM."""


class OrderNotFound(DomainError):
    pass


class OrderNotAccessible(DomainError):
    """Pedido existe, mas não pertence ao cliente.

    A camada de ferramentas deve traduzir isto para a MESMA mensagem
    de OrderNotFound, para não revelar a existência do pedido.
    """


class DuplicateRefund(DomainError):
    pass


class OutsideClaimWindow(DomainError):
    pass


class InvalidStatus(DomainError):
    pass


class ItemNotFound(DomainError):
    pass


class ValueAboveLimit(DomainError):
    pass