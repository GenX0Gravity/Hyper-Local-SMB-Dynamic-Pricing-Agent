"""Tests for Dynamic Pricing Engine."""

from datetime import datetime, timezone
from uuid import uuid4

from backend.services.dynamic_pricing.algorithm import DynamicPricingAlgorithm
from backend.services.dynamic_pricing.constraints import PricingConstraints
from backend.services.dynamic_pricing.schemas import PricingInputs, PricingActionType
from backend.models.product import Product


def _product(**kwargs) -> Product:
    defaults = dict(
        id=uuid4(),
        tenant_id=uuid4(),
        name="Vanilla Latte",
        category="Beverages",
        cost_price=1.20,
        base_price=4.50,
        current_price=4.50,
        min_price=3.50,
        max_price=6.50,
        stock_qty=200,
    )
    defaults.update(kwargs)
    return Product(**defaults)


def test_margin_floor_blocks_excessive_discount():
    constraints = PricingConstraints(min_margin_pct=15.0, max_discount_pct=30.0)
    discount, price, notes = constraints.apply_discount_cap(
        base_price=4.50,
        cost_price=1.20,
        discount_pct=30.0,
    )
    margin = constraints.margin_at_price(price, 1.20)
    assert margin >= 15.0
    assert discount <= 30.0
    assert any("margin" in n.lower() for n in notes) or discount < 30.0


def test_max_discount_cap():
    constraints = PricingConstraints(max_discount_pct=30.0)
    discount, _, notes = constraints.apply_discount_cap(
        base_price=10.0, cost_price=1.0, discount_pct=50.0
    )
    assert discount == 30.0
    assert any("capped" in n.lower() for n in notes)


def test_high_demand_triggers_increase():
    algo = DynamicPricingAlgorithm()
    product = _product()
    inputs = PricingInputs(
        demand_score=85.0,
        inventory_level=30,
        inventory_score=85.0,
        event_score=75.0,
        weather_score=70.0,
    )
    decision = algo.evaluate_product(product, inputs)
    assert decision.price_increase_pct > 0 or decision.pricing_pressure > 0.1
    assert len(decision.explanations) >= 3


def test_low_demand_triggers_discount():
    algo = DynamicPricingAlgorithm()
    product = _product(stock_qty=500)
    inputs = PricingInputs(
        demand_score=25.0,
        inventory_level=500,
        inventory_score=15.0,
        event_score=5.0,
        weather_score=40.0,
    )
    decision = algo.evaluate_product(product, inputs)
    assert decision.discount_pct > 0
    assert decision.discount_pct <= 30.0
    assert decision.action_type == PricingActionType.DISCOUNT


def test_discount_never_below_margin():
    algo = DynamicPricingAlgorithm(
        constraints=PricingConstraints(min_margin_pct=20.0, max_discount_pct=30.0)
    )
    product = _product(cost_price=3.50, base_price=4.00, min_price=3.80)
    inputs = PricingInputs(
        demand_score=10.0,
        inventory_level=900,
        inventory_score=5.0,
        event_score=0.0,
        weather_score=30.0,
    )
    decision = algo.evaluate_product(product, inputs)
    assert decision.margin_pct >= 20.0 - 0.1


def test_inventory_score_scarcity():
    algo = DynamicPricingAlgorithm()
    assert algo.inventory_score(10) > algo.inventory_score(200)


def test_pressure_computation():
    algo = DynamicPricingAlgorithm()
    high = PricingInputs(demand_score=90, inventory_level=20, inventory_score=90, event_score=80, weather_score=75)
    low = PricingInputs(demand_score=20, inventory_level=500, inventory_score=10, event_score=0, weather_score=30)
    assert algo.compute_pressure(high) > algo.compute_pressure(low)


def test_explanations_present():
    algo = DynamicPricingAlgorithm()
    decision = algo.evaluate_product(
        _product(),
        PricingInputs(demand_score=60, inventory_level=100, inventory_score=50, event_score=40, weather_score=55),
    )
    factors = {e.factor for e in decision.explanations}
    assert "demand_score" in factors
    assert "inventory" in factors
    assert decision.summary
