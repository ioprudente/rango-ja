class DomainError(Exception): pass
class OrderNotFound(DomainError): pass
class OrderFromAnotherCustomer(DomainError): pass
class ClaimOutOfTimeframe(DomainError): pass
class DuplicateRefund(DomainError): pass
class ItemNotFoundInOrder(DomainError): pass
class ValueExceedsLimit(DomainError):
    def __init__(self, value: float, limit: float) -> None:
        self.value = value
        self.limit = limit
        super().__init__(f"Reembolso de R$ {value:.2f} excede o limite de R$ {limit:.2f}.")
class UnsupportedReason(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.reason = message
