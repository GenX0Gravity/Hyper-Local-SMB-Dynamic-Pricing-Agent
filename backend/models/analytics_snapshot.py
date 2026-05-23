"""Persisted weekly / monthly analytics reports."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class AnalyticsSnapshot(SQLModel, table=True):
    __tablename__ = "analytics_snapshots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    period_type: str = Field(max_length=20, index=True)  # weekly | monthly
    period_start: datetime = Field(index=True)
    period_end: datetime = Field(index=True)
    label: str = Field(max_length=64)  # e.g. "2026-W21" or "2026-05"
    metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
