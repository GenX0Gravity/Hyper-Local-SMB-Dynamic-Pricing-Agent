import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlmodel import Session, select
from backend.models.product import Product
from backend.models.rule import PricingRule
from backend.models.signal import DemandSignal
from backend.models.recommendation import Recommendation

logger = logging.getLogger(__name__)

class PricingEngine:
    @staticmethod
    def evaluate_rules(
        session: Session,
        tenant_id: UUID,
        active_signals: List[DemandSignal]
    ) -> List[Recommendation]:
        """
        Runs the pricing rules engine for a tenant's product catalog.
        Analyzes signals (weather, events) and inventory levels, calculates optimized prices,
        and saves Recommendations.
        """
        # Fetch active products & rules
        products = session.exec(
            select(Product).where(Product.tenant_id == tenant_id)
        ).all()
        
        rules = session.exec(
            select(PricingRule).where(
                PricingRule.tenant_id == tenant_id,
                PricingRule.is_active == True
            )
        ).all()

        if not products or not rules:
            logger.info(f"No products or active rules found for tenant {tenant_id}.")
            return []

        # Parse signals into helper maps for quick validation
        weather_signal = None
        event_signals = []
        for signal in active_signals:
            if signal.signal_type == "weather":
                weather_signal = signal.value
            elif signal.signal_type == "event":
                event_signals.append(signal.value)

        generated_recommendations = []
        now = datetime.now(timezone.utc)

        # Helper method to evaluate if a single rule applies
        for product in products:
            applicable_rules = []
            
            for rule in rules:
                # Basic scope filter (rules can target specific products or categories)
                target_category = rule.conditions.get("category")
                target_product_id = rule.conditions.get("product_id")
                
                if target_product_id and str(target_product_id) != str(product.id):
                    continue
                if target_category and product.category != target_category:
                    continue
                
                # Check rule condition based on type
                rule_applies = False
                
                if rule.rule_type == "weather" and weather_signal:
                    rule_applies = PricingEngine._check_weather_rule(rule.conditions, weather_signal)
                
                elif rule.rule_type == "event" and event_signals:
                    rule_applies = PricingEngine._check_event_rule(rule.conditions, event_signals)
                
                elif rule.rule_type == "inventory":
                    rule_applies = PricingEngine._check_inventory_rule(rule.conditions, product.stock_qty)
                
                elif rule.rule_type == "time_of_day":
                    rule_applies = PricingEngine._check_time_rule(rule.conditions, now)

                if rule_applies:
                    applicable_rules.append(rule)

            # Apply rule adjustments (if multiple apply, pick the highest upward adjustment or compound)
            # For simplicity, we apply the rule with the highest absolute recommended price
            if not applicable_rules:
                continue
                
            best_recommended_price = product.base_price
            triggering_rule: Optional[PricingRule] = None
            reason_parts = []

            for rule in applicable_rules:
                adjusted_price = product.base_price
                if rule.adjustment_type == "percentage":
                    # e.g. adjustment_value = 10.0 => +10%, -5.0 => -5%
                    multiplier = 1 + (rule.adjustment_value / 100.0)
                    adjusted_price = product.base_price * multiplier
                elif rule.adjustment_type == "fixed":
                    adjusted_price = product.base_price + rule.adjustment_value
                
                # Enforce price floors and ceilings
                floor = product.min_price if product.min_price is not None else product.cost_price
                ceiling = product.max_price if product.max_price is not None else (product.base_price * 2.0)
                
                final_price = max(floor, min(adjusted_price, ceiling))
                final_price = round(final_price, 2)

                if final_price != round(product.current_price, 2):
                    if final_price > best_recommended_price or triggering_rule is None:
                        best_recommended_price = final_price
                        triggering_rule = rule
                        reason_parts = [
                            f"Rule '{rule.name}' triggered: {rule.rule_type.replace('_', ' ').title()} trigger."
                        ]

            if triggering_rule and round(best_recommended_price, 2) != round(product.current_price, 2):
                # Check if there is already a pending recommendation for this product
                existing_recommendation = session.exec(
                    select(Recommendation).where(
                        Recommendation.product_id == product.id,
                        Recommendation.status == "pending"
                    )
                ).first()

                if existing_recommendation:
                    # Update existing pending suggestion if recommendation values changed
                    if round(existing_recommendation.recommended_price, 2) != round(best_recommended_price, 2):
                        existing_recommendation.recommended_price = best_recommended_price
                        existing_recommendation.rule_id = triggering_rule.id
                        existing_recommendation.reason = " & ".join(reason_parts)
                        existing_recommendation.expires_at = now + timedelta(hours=12)
                        session.add(existing_recommendation)
                        generated_recommendations.append(existing_recommendation)
                else:
                    new_recommendation = Recommendation(
                        tenant_id=tenant_id,
                        product_id=product.id,
                        rule_id=triggering_rule.id,
                        recommended_price=best_recommended_price,
                        previous_price=product.current_price,
                        reason=" & ".join(reason_parts),
                        status="pending",
                        expires_at=now + timedelta(hours=12)
                    )
                    session.add(new_recommendation)
                    generated_recommendations.append(new_recommendation)
                    
        session.commit()
        return generated_recommendations

    @staticmethod
    def _check_weather_rule(conditions: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """
        Conditions format: {"condition": "Rainy", "temp_below": 15, "temp_above": 32}
        """
        target_condition = conditions.get("weather")
        temp_below = conditions.get("temp_below")
        temp_above = conditions.get("temp_above")
        
        current_condition = weather.get("condition")
        current_temp = weather.get("temp")
        
        # Check condition
        if target_condition and current_condition and target_condition.lower() != current_condition.lower():
            return False
            
        # Check temperature thresholds
        if temp_below is not None and current_temp is not None and current_temp >= temp_below:
            return False
            
        if temp_above is not None and current_temp is not None and current_temp <= temp_above:
            return False
            
        return True

    @staticmethod
    def _check_event_rule(conditions: Dict[str, Any], events: List[Dict[str, Any]]) -> bool:
        """
        Conditions format: {"attendance_above": 2000, "category": "concerts", "radius_km": 1.0}
        """
        min_attendance = conditions.get("attendance_above", 0)
        target_category = conditions.get("event_category") # 'concerts', 'sports', etc.
        max_distance = conditions.get("radius_km")

        for event in events:
            # Validate attendance
            if event.get("attendance", 0) < min_attendance:
                continue
                
            # Validate category
            if target_category and event.get("category") != target_category:
                continue
                
            # Validate distance
            if max_distance is not None and event.get("distance_km", 999.0) > max_distance:
                continue
                
            # Found matching event
            return True
            
        return False

    @staticmethod
    def _check_inventory_rule(conditions: Dict[str, Any], stock_qty: int) -> bool:
        """
        Conditions format: {"stock_below": 10, "stock_above": 100}
        """
        stock_below = conditions.get("stock_below")
        stock_above = conditions.get("stock_above")

        if stock_below is not None and stock_qty >= stock_below:
            return False
            
        if stock_above is not None and stock_qty <= stock_above:
            return False
            
        return True

    @staticmethod
    def _check_time_rule(conditions: Dict[str, Any], current_time: datetime) -> bool:
        """
        Conditions format: {"hour_start": 14, "hour_end": 17, "days_of_week": [1, 2, 3, 4, 5]}
        """
        hour_start = conditions.get("hour_start")
        hour_end = conditions.get("hour_end")
        days = conditions.get("days_of_week") # Monday=0, Sunday=6
        
        if hour_start is not None and current_time.hour < hour_start:
            return False
            
        if hour_end is not None and current_time.hour >= hour_end:
            return False
            
        if days is not None and current_time.weekday() not in days:
            return False
            
        return True
