"""Pricing constraints — margin floor and maximum discount."""

from __future__ import annotations

from backend.core.config import settings


class PricingConstraints:
    """Enforces hard limits on price adjustments."""

    def __init__(
        self,
        min_margin_pct: float | None = None,
        max_discount_pct: float | None = None,
        max_increase_pct: float | None = None,
    ):
        self.min_margin_pct = min_margin_pct or settings.PRICING_MIN_MARGIN_PCT
        self.max_discount_pct = max_discount_pct or settings.PRICING_MAX_DISCOUNT_PCT
        self.max_increase_pct = max_increase_pct or settings.PRICING_MAX_INCREASE_PCT

    def min_price_for_margin(self, cost_price: float) -> float:
        """Lowest price that preserves minimum margin %."""
        if cost_price <= 0:
            return 0.01
        # margin = (price - cost) / price  =>  price = cost / (1 - margin)
        margin_frac = self.min_margin_pct / 100.0
        if margin_frac >= 1.0:
            return cost_price * 1.01
        return round(cost_price / (1.0 - margin_frac), 2)

    def margin_at_price(self, price: float, cost_price: float) -> float:
        if price <= 0:
            return 0.0
        return round(((price - cost_price) / price) * 100.0, 2)

    def apply_discount_cap(
        self,
        base_price: float,
        cost_price: float,
        discount_pct: float,
        min_price_floor: float | None = None,
        max_price_ceiling: float | None = None,
    ) -> tuple[float, float, list[str]]:
        """
        Returns (final_discount_pct, recommended_price, constraints_applied).
        """
        applied: list[str] = []
        discount = min(discount_pct, self.max_discount_pct)
        if discount_pct > self.max_discount_pct:
            applied.append(
                f"Discount capped at {self.max_discount_pct}% (requested {discount_pct:.1f}%)"
            )

        price = base_price * (1.0 - discount / 100.0)
        margin_floor_price = self.min_price_for_margin(cost_price)
        effective_floor = margin_floor_price
        if min_price_floor is not None:
            effective_floor = max(effective_floor, min_price_floor)

        if price < effective_floor:
            price = effective_floor
            discount = max(0.0, (1.0 - price / base_price) * 100.0) if base_price > 0 else 0.0
            applied.append(
                f"Discount reduced to {discount:.1f}% to maintain "
                f"{self.min_margin_pct}% minimum margin"
            )

        if max_price_ceiling is not None:
            price = min(price, max_price_ceiling)

        return round(discount, 2), round(price, 2), applied

    def apply_increase_cap(
        self,
        base_price: float,
        increase_pct: float,
        max_price_ceiling: float | None = None,
    ) -> tuple[float, float, list[str]]:
        applied: list[str] = []
        increase = min(increase_pct, self.max_increase_pct)
        if increase_pct > self.max_increase_pct:
            applied.append(
                f"Increase capped at {self.max_increase_pct}% (requested {increase_pct:.1f}%)"
            )

        price = base_price * (1.0 + increase / 100.0)
        if max_price_ceiling is not None:
            if price > max_price_ceiling:
                price = max_price_ceiling
                increase = max(0.0, (price / base_price - 1.0) * 100.0) if base_price > 0 else 0.0
                applied.append(f"Price capped at ceiling ${max_price_ceiling:.2f}")

        return round(increase, 2), round(price, 2), applied
