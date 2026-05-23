"""Tests for XGBoost demand forecasting service."""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlmodel import SQLModel, create_engine, Session

from backend.forecasting.features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    row_to_features,
    units_to_demand_score,
)
from backend.forecasting.evaluator import evaluate_predictions
from backend.forecasting.dataset import build_training_dataframe
from backend.forecasting.model_store import ModelStore
from backend.forecasting.trainer import ForecastTrainer
from backend.forecasting.schemas import TrainRequest
from backend.forecasting.service import DemandForecastingService
from backend.models.tenant import Tenant
from backend.models.product import Product
from backend.models.sales_history import SalesHistory
from backend.models.signal import DemandSignal
from backend.models.forecast_model import ForecastModelRun


@pytest.fixture(name="session")
def session_fixture(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        tenant = Tenant(
            name="Test Cafe",
            business_type="cafe",
            latitude=40.71,
            longitude=-74.0,
            timezone="UTC",
        )
        session.add(tenant)
        session.flush()

        product = Product(
            tenant_id=tenant.id,
            name="Latte",
            cost_price=1.0,
            base_price=4.0,
            current_price=4.0,
            category="Beverages",
        )
        session.add(product)
        session.flush()

        now = datetime.now(timezone.utc)
        for days in range(14):
            for hour in range(8, 20):
                sold_at = now - timedelta(days=days, hours=hour)
                session.add(
                    SalesHistory(
                        tenant_id=tenant.id,
                        product_id=product.id,
                        quantity=5 + (hour % 5),
                        price_sold=4.0,
                        sold_at=sold_at,
                    )
                )
        session.add(
            DemandSignal(
                tenant_id=tenant.id,
                signal_type="weather",
                value={"temp": 22, "condition": "Clear"},
                recorded_at=now,
            )
        )
        session.commit()
        yield session, tenant, tmp_path


def test_feature_engineering_time_and_weather():
    ts = pd.Timestamp("2024-06-15 14:30:00", tz="UTC")
    feats = row_to_features(
        ts,
        weather={"temp": 28, "condition": "Rainy", "humidity": 80},
        footfall={"busy_percent": 75, "visitor_index": 1.4},
        events=[{"attendance": 5000, "impact_score": 0.8}],
        sales_lag_1h=10,
        sales_lag_24h=8,
        sales_rolling_7d_mean=9,
        sales_rolling_7d_std=2,
    )
    assert set(FEATURE_COLUMNS).issubset(feats.keys())
    assert feats["hour_of_day"] == 14
    assert feats["day_of_week"] == 5  # Saturday
    assert feats["weather_rain"] == 1.0
    assert feats["event_count"] == 1.0


def test_demand_score_scaling():
    scores = units_to_demand_score(np.array([0, 50, 100]), 0, 100)
    assert list(scores) == [0.0, 50.0, 100.0]


def test_evaluation_metrics():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 28.0])
    metrics = evaluate_predictions(y_true, y_pred, 0, 40, train_rows=2, test_rows=1)
    assert metrics.mae > 0
    assert metrics.rmse > 0
    assert 0 <= metrics.demand_score_mae <= 100


def test_build_training_dataframe(session):
    db, tenant, _ = session
    df = build_training_dataframe(db, tenant.id, lookback_days=30)
    assert len(df) >= 48
    assert TARGET_COLUMN in df.columns or "demand_units" in df.columns


def test_train_and_predict(session):
    db, tenant, tmp_path = session
    store = ModelStore(base_dir=str(tmp_path / "models"))
    trainer = ForecastTrainer(store=store)
    result = trainer.train(db, tenant.id, lookback_days=30, force=True)
    assert result.model_version
    assert result.metrics.train_rows > 0
    assert result.metrics.r2 is not None

    artifact = store.load(tenant.id)
    assert artifact is not None
    assert artifact.metrics.test_rows >= 1


def test_service_predict(session):
    import asyncio
    from backend.forecasting.predictor import DemandPredictor
    from backend.forecasting.schemas import PredictRequest

    db, tenant, tmp_path = session
    service = DemandForecastingService()
    service.store = ModelStore(base_dir=str(tmp_path / "models2"))
    service.trainer = ForecastTrainer(store=service.store)
    service.predictor = DemandPredictor(service.store)

    service.train(db, tenant.id, TrainRequest(lookback_days=30, force=True))

    pred = asyncio.run(
        service.predict(
            db,
            tenant.id,
            PredictRequest(
                weather={"temp": 25, "condition": "Sunny"},
                footfall={"busy_percent": 60},
                events=[],
            ),
        )
    )
    assert 0 <= pred.demand_score <= 100
    assert pred.predicted_units >= 0
