"""Persist and load XGBoost model artifacts per tenant."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import joblib
from xgboost import XGBRegressor

from backend.core.config import settings
from backend.forecasting.schemas import EvaluationMetrics

logger = logging.getLogger(__name__)


class ModelArtifact:
    def __init__(
        self,
        model: XGBRegressor,
        metadata: dict[str, Any],
        metrics: EvaluationMetrics,
    ):
        self.model = model
        self.metadata = metadata
        self.metrics = metrics


class ModelStore:
    def __init__(self, base_dir: str | None = None):
        root = base_dir or settings.FORECAST_MODEL_DIR
        self.base_path = Path(root)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def tenant_dir(self, tenant_id: UUID) -> Path:
        path = self.base_path / str(tenant_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _paths(self, tenant_id: UUID, version: str) -> tuple[Path, Path, Path]:
        d = self.tenant_dir(tenant_id)
        prefix = d / version
        return (
            Path(f"{prefix}_model.joblib"),
            Path(f"{prefix}_metadata.json"),
            Path(f"{prefix}_metrics.json"),
        )

    def save(
        self,
        tenant_id: UUID,
        model: XGBRegressor,
        metadata: dict[str, Any],
        metrics: EvaluationMetrics,
        version: str | None = None,
    ) -> str:
        version = version or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_path, meta_path, metrics_path = self._paths(tenant_id, version)

        joblib.dump(model, model_path)
        meta_path.write_text(json.dumps(metadata, indent=2, default=str))
        metrics_path.write_text(metrics.model_dump_json(indent=2))

        latest = self.tenant_dir(tenant_id) / "latest.json"
        latest.write_text(
            json.dumps(
                {
                    "version": version,
                    "trained_at": metadata.get("trained_at"),
                    "model_path": str(model_path),
                },
                indent=2,
            )
        )
        logger.info("Saved forecast model %s for tenant %s", version, tenant_id)
        return version

    def load(self, tenant_id: UUID, version: str | None = None) -> Optional[ModelArtifact]:
        if version is None:
            latest_file = self.tenant_dir(tenant_id) / "latest.json"
            if not latest_file.exists():
                return None
            version = json.loads(latest_file.read_text()).get("version")
            if not version:
                return None

        model_path, meta_path, metrics_path = self._paths(tenant_id, version)
        if not model_path.exists():
            return None

        model = joblib.load(model_path)
        metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        metrics = (
            EvaluationMetrics.model_validate_json(metrics_path.read_text())
            if metrics_path.exists()
            else EvaluationMetrics(
                mae=0,
                rmse=0,
                r2=0,
                mape_pct=0,
                demand_score_mae=0,
                train_rows=0,
                test_rows=0,
            )
        )
        return ModelArtifact(model=model, metadata=metadata, metrics=metrics)

    def has_model(self, tenant_id: UUID) -> bool:
        return (self.tenant_dir(tenant_id) / "latest.json").exists()
