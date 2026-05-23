"""WhatsApp message templates for PricePulse Business Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


class MessageTemplates:
    """Formatted outbound messages — plain text for Twilio WhatsApp."""

    BRAND = "PricePulse AI"

    @classmethod
    def pricing_recommendation(
        cls,
        *,
        store_name: str,
        headline: str,
        product_name: str,
        category: str | None,
        current_price: float,
        recommended_price: float,
        discount_pct: float = 0.0,
        increase_pct: float = 0.0,
        currency: str = "USD",
        index: int = 1,
        total: int = 1,
    ) -> str:
        sym = "$" if currency == "USD" else f"{currency} "
        change = ""
        if discount_pct > 0:
            change = f"Suggest *{discount_pct:.0f}% discount*"
        elif increase_pct > 0:
            change = f"Suggest *{increase_pct:.0f}% price increase*"
        else:
            change = "Suggest price adjustment"

        cat = f" ({category})" if category else ""
        return (
            f"*{cls.BRAND}* — {store_name}\n"
            f"[{index}/{total}] {headline}\n\n"
            f"{change} on *{product_name}*{cat}.\n"
            f"Current: {sym}{current_price:.2f} → Recommended: {sym}{recommended_price:.2f}\n\n"
            f"Reply *APPROVE {index}* or *REJECT {index}*"
        )

    @classmethod
    def weather_alert(
        cls,
        *,
        store_name: str,
        condition: str,
        time_label: str,
        discount_pct: float,
        category: str = "tea & hot beverages",
    ) -> str:
        """Sample: Heavy rain expected at 4 PM. Suggest 20% discount on tea products."""
        return (
            f"*{cls.BRAND}* — {store_name}\n\n"
            f"*{condition}* expected {time_label}.\n"
            f"Suggest *{discount_pct:.0f}% discount* on {category}.\n\n"
            f"Reply *APPROVE* to apply or *REJECT* to skip."
        )

    @classmethod
    def batch_header(cls, store_name: str, count: int) -> str:
        return (
            f"*{cls.BRAND}* — {store_name}\n"
            f"You have *{count}* new pricing recommendation(s):\n"
            f"{'─' * 28}"
        )

    @classmethod
    def batch_footer(cls, auto_approve: bool = False) -> str:
        if auto_approve:
            return "Auto-approve is ON — changes apply automatically."
        return (
            "Reply:\n"
            "• *APPROVE* or *APPROVE 1* — accept\n"
            "• *REJECT* or *REJECT 1* — decline\n"
            "• *APPROVE ALL* / *REJECT ALL*\n"
            "• *HELP* — commands"
        )

    @classmethod
    def approval_confirmed(
        cls,
        product_name: str,
        new_price: float,
        currency: str = "USD",
    ) -> str:
        sym = "$" if currency == "USD" else f"{currency} "
        return (
            f"Approved. *{product_name}* is now {sym}{new_price:.2f}.\n"
            f"Change is live on your menu."
        )

    @classmethod
    def rejection_confirmed(cls, product_name: str) -> str:
        return f"Rejected pricing change for *{product_name}*. No changes made."

    @classmethod
    def auto_approve_enabled(cls, store_name: str) -> str:
        return (
            f"*{cls.BRAND}* — {store_name}\n"
            f"Auto-approve mode is now *ON*.\n"
            f"Future recommendations will apply automatically."
        )

    @classmethod
    def auto_approve_disabled(cls, store_name: str) -> str:
        return (
            f"*{cls.BRAND}* — {store_name}\n"
            f"Auto-approve mode is now *OFF*.\n"
            f"You will be asked to approve each suggestion."
        )

    @classmethod
    def daily_summary(
        cls,
        *,
        store_name: str,
        date_label: str,
        pending_count: int,
        approved_count: int,
        rejected_count: int,
        top_insight: str,
        weather_line: str | None = None,
        event_line: str | None = None,
        revenue_hint: str | None = None,
    ) -> str:
        lines = [
            f"*{cls.BRAND} — Daily Summary*",
            f"{store_name} · {date_label}",
            "",
            f"Pending: {pending_count} | Approved: {approved_count} | Rejected: {rejected_count}",
        ]
        if weather_line:
            lines.extend(["", f"Weather: {weather_line}"])
        if event_line:
            lines.append(f"Events: {event_line}")
        lines.extend(["", f"Insight: {top_insight}"])
        if revenue_hint:
            lines.extend(["", revenue_hint])
        lines.extend(["", "Reply *SUMMARY* anytime · *HELP* for commands"])
        return "\n".join(lines)

    @classmethod
    def help_text(cls) -> str:
        return (
            f"*{cls.BRAND} Commands*\n\n"
            "*APPROVE* — accept latest suggestion\n"
            "*APPROVE 1* — accept item #1\n"
            "*APPROVE ALL* — accept all pending\n"
            "*REJECT* / *REJECT 1* / *REJECT ALL*\n"
            "*AUTO ON* — auto-apply future prices\n"
            "*AUTO OFF* — manual approval\n"
            "*SUMMARY* — daily report\n"
            "*STATUS* — pending count\n"
            "*HELP* — this message"
        )

    @classmethod
    def status(cls, pending: int, auto_approve: bool) -> str:
        mode = "ON" if auto_approve else "OFF"
        return f"Pending recommendations: *{pending}*\nAuto-approve: *{mode}*"

    @classmethod
    def no_pending(cls) -> str:
        return "No pending pricing recommendations right now."

    @classmethod
    def unknown_command(cls) -> str:
        return "Sorry, I didn't understand that. Reply *HELP* for available commands."

    @classmethod
    def unauthorized_phone(cls) -> str:
        return "This number is not registered with PricePulse. Contact your store admin."

    @staticmethod
    def format_time_label(when: datetime | None) -> str:
        if not when:
            return "soon"
        hour = when.hour % 12 or 12
        ampm = "AM" if when.hour < 12 else "PM"
        return f"at {hour} {ampm}"
