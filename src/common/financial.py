"""
Financial Computation Engine — Sprint 6.
Single source of truth for all commission/net math.
Called from:
  - POST /enrollments/:id/confirm-payment
  - POST /subscriptions/:id/renew
Never reimplemented inline.
"""
from decimal import Decimal, ROUND_HALF_UP


def compute_financials(
    amount: Decimal,
    commission_percent: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Returns (commission_amount, net_amount), both rounded to 2dp using ROUND_HALF_UP.
    This is the canonical computation — matches what ConfirmPaymentDialog previews client-side.
    """
    commission_amount = (
        amount * commission_percent / Decimal(100)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net_amount = amount - commission_amount
    return commission_amount, net_amount


def resolve_effective_commission(class_, teacher) -> Decimal:
    """
    class.commission_percent ?? teacher.default_commission_percent ?? 0
    Identical to ClassResponse.effectiveCommissionPercent resolution in Sprint 4.
    """
    if class_ is not None and class_.commission_percent is not None:
        return Decimal(str(class_.commission_percent))
    if teacher is not None and teacher.default_commission_percent is not None:
        return Decimal(str(teacher.default_commission_percent))
    return Decimal("0")
