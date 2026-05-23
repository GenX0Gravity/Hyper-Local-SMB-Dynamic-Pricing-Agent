"""
Training dataset builder — joins sales history with signal snapshots.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from backend.forecasting.features import (
    TARGET_COLUMN,
    row_to_features,
    units_to_demand_score,
)
from backend.models.signal import DemandSignal
from backend.models.sales_history import SalesHistory
from backend.models.tenant import Tenant

logger = logging.getLogger(__name__)


def _nearest_signal(
    signals: list[DemandSignal],
    signal_type: str,
    ts: datetime,
    max_delta_hours: int = 3,
) -> dict[str, Any] | None:
    candidates = [s for s in signals if s.signal_type == signal_type]
    if not candidates:
        return None
    best = min(
        candidates,
        key=lambda s: abs((s.recorded_at - ts).total_seconds()),
    )
    if abs((best.recorded_at - ts).total_seconds()) > max_delta_hours * 3600:
        return None
    return best.value


def _aggregate_sales_hourly(
    session: Session,
    tenant_id: UUID,
    lookback_days: int,
    product_id: UUID | None = None,
) -> pd.DataFrame:
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    query = select(SalesHistory).where(
        SalesHistory.tenant_id == tenant_id,
        SalesHistory.sold_at >= since,
    )
    if product_id:
        query = query.where(SalesHistory.product_id == product_id)
    sales = session.exec(query).all()

    if not sales:
        return pd.DataFrame()

    rows = [
        {
            "ts": s.sold_at.replace(minute=0, second=0, microsecond=0),
            "demand_units": float(s.quantity),
        }
        for s in sales
    ]
    df = pd.DataFrame(rows)
    hourly = df.groupby("ts", as_index=False)["demand_units"].sum()
    hourly["ts"] = pd.to_datetime(hourly["ts"], utc=True)
    return hourly.sort_values("ts").reset_index(drop=True)


def _augment_sparse_data(hourly: pd.DataFrame, tenant: Tenant) -> pd.DataFrame:
    """Bootstrap hourly rows when real history is too thin for XGBoost."""
    if len(hourly) >= 48:
        return hourly

    logger.info("Augmenting sparse sales data for tenant %s", tenant.id)
    now = datetime.now(timezone.utc)
    base_units = float(hourly["demand_units"].mean()) if len(hourly) else 12.0
    rows = []
    for days_back in range(30, 0, -1):
        for hour in range(6, 22):
            ts = (now - timedelta(days=days_back)).replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            dow = ts.weekday()
            weekend_boost = 1.2 if dow >= 5 else 1.0
            peak = 1.3 if hour in (8, 9, 12, 13, 17, 18) else 0.85
            noise = np.random.default_rng(int(ts.timestamp()) % 10_000).normal(0, 0.08)
            units = max(1.0, base_units * weekend_boost * peak * (1 + noise))
            rows.append({"ts": ts, "demand_units": units})
    aug = pd.DataFrame(rows)
    if len(hourly):
        aug = pd.concat([hourly, aug], ignore_index=True)
    return aug.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)


def _add_lag_features(hourly: pd.DataFrame) -> pd.DataFrame:
    hourly = hourly.copy()
    hourly = hourly.set_index("ts").sort_index()
    hourly["sales_lag_1h"] = hourly["demand_units"].shift(1).fillna(0)
    hourly["sales_lag_24h"] = hourly["demand_units"].shift(24).fillna(0)
    hourly["sales_rolling_7d_mean"] = (
        hourly["demand_units"].rolling(window=24 * 7, min_periods=1).mean()
    )
    hourly["sales_rolling_7d_std"] = (
        hourly["demand_units"].rolling(window=24 * 7, min_periods=1).std().fillna(0)
    )
    return hourly.reset_index()


def build_training_dataframe(
    session: Session,
    tenant_id: UUID,
    lookback_days: int = 90,
    product_id: UUID | None = None,
) -> pd.DataFrame:
    tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    hourly = _aggregate_sales_hourly(session, tenant_id, lookback_days, product_id)
    hourly = _augment_sparse_data(hourly, tenant)
    hourly = _add_lag_features(hourly)

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    signals = session.exec(
        select(DemandSignal).where(
            DemandSignal.tenant_id == tenant_id,
            DemandSignal.recorded_at >= since,
        )
    ).all()

    event_signals = [
        s for s in signals if s.signal_type == "event"
    ]
    weather_signals = [s for s in signals if s.signal_type == "weather"]
    footfall_signals = [
        s for s in signals if s.signal_type in ("foot_traffic", "footfall")
    ]

    records: list[dict[str, Any]] = []
    for _, row in hourly.iterrows():
        ts = row["ts"].to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        weather = _nearest_signal(weather_signals, "weather", ts)
        footfall = _nearest_signal(footfall_signals, "foot_traffic", ts) or _nearest_signal(
            footfall_signals, "footfall", ts
        )

        # Events within ±6h window
        nearby_events = [
            s.value
            for s in event_signals
            if abs((s.recorded_at - ts).total_seconds()) <= 6 * 3600
        ]

        feats = row_to_features(
            pd.Timestamp(ts),
            weather=weather,
            footfall=footfall,
            events=nearby_events,
            sales_lag_1h=float(row["sales_lag_1h"]),
            sales_lag_24h=float(row["sales_lag_24h"]),
            sales_rolling_7d_mean=float(row["sales_rolling_7d_mean"]),
            sales_rolling_7d_std=float(row["sales_rolling_7d_std"]),
        )
        feats[TARGET_COLUMN] = float(row["demand_units"])
        feats["ts"] = ts
        records.append(feats)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    p5 = float(df[TARGET_COLUMN].quantile(0.05))
    p95 = float(df[TARGET_COLUMN].quantile(0.95))
    df["scale_min"] = p5
    df["scale_max"] = p95
    df["demand_score"] = units_to_demand_score(
        df[TARGET_COLUMN].values, p5, p95
    )
    return df
