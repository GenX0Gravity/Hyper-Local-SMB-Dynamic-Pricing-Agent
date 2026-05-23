"""Tests for WhatsApp Business Agent."""

from backend.services.whatsapp_agent.parser import CommandType, InboundCommandParser
from backend.services.whatsapp_agent.templates import MessageTemplates


def test_parser_approve():
    p = InboundCommandParser()
    assert p.parse("APPROVE").type == CommandType.APPROVE
    assert p.parse("yes").type == CommandType.APPROVE
    assert p.parse("APPROVE 2").index == 2
    assert p.parse("3").type == CommandType.APPROVE
    assert p.parse("3").index == 3


def test_parser_reject_all():
    p = InboundCommandParser()
    assert p.parse("REJECT ALL").type == CommandType.REJECT_ALL
    assert p.parse("approve all").type == CommandType.APPROVE_ALL


def test_parser_auto_and_summary():
    p = InboundCommandParser()
    assert p.parse("AUTO ON").type == CommandType.AUTO_ON
    assert p.parse("auto off").type == CommandType.AUTO_OFF
    assert p.parse("summary").type == CommandType.SUMMARY
    assert p.parse("help").type == CommandType.HELP


def test_weather_alert_template():
    msg = MessageTemplates.weather_alert(
        store_name="Daily Brew",
        condition="Heavy rain",
        time_label="at 4 PM",
        discount_pct=20.0,
        category="tea products",
    )
    assert "Heavy rain" in msg
    assert "4 PM" in msg
    assert "20%" in msg
    assert "tea products" in msg


def test_pricing_recommendation_template():
    msg = MessageTemplates.pricing_recommendation(
        store_name="Cafe",
        headline="Rain playbook",
        product_name="Masala Chai",
        category="Beverages",
        current_price=4.0,
        recommended_price=3.2,
        discount_pct=20.0,
        index=1,
        total=2,
    )
    assert "Masala Chai" in msg
    assert "APPROVE 1" in msg


def test_daily_summary_template():
    msg = MessageTemplates.daily_summary(
        store_name="Store",
        date_label="Mon 01 Jan 2026",
        pending_count=2,
        approved_count=5,
        rejected_count=1,
        top_insight="Event nearby",
    )
    assert "Pending: 2" in msg
    assert "Event nearby" in msg
