# Demand Forecasting Service (XGBoost)

## Overview

Predicts **demand score (0–100)** from sales history and live signals using an **XGBRegressor**.

## Inputs → Features

| Source | Features |
|--------|----------|
| Historical sales | `sales_lag_1h`, `sales_lag_24h`, `sales_rolling_7d_mean/std` |
| Weather | `temperature_c`, `humidity_pct`, `wind_speed`, rain/clear/cloud flags |
| Footfall | `footfall_busy_pct`, `footfall_visitor_index` |
| Events | `event_count`, `event_max_attendance`, `event_impact_score` |
| Time | `hour_of_day`, `day_of_week`, sin/cos encodings, `is_weekend` |

Target: hourly `demand_units` (sum of quantities). Score = percentile scale to 0–100.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/forecast/train` | Training pipeline |
| POST | `/api/v1/forecast/retrain` | Force retrain (new version) |
| POST | `/api/v1/forecast/predict` | Single prediction |
| GET | `/api/v1/forecast/predict/batch` | All products |
| GET | `/api/v1/forecast/metrics` | MAE, RMSE, R², MAPE, score MAE |

## Pipelines

```
Training:  sales + signals → feature matrix → train/test split → XGBoost → artifacts
Predict:   live signals + lags → vector → model → units → demand_score
Retrain:   same as train with force=true (Celery weekly)
```

## Artifacts

```
data/models/forecasting/{tenant_id}/
  {version}_model.joblib
  {version}_metadata.json
  {version}_metrics.json
  latest.json
```

## Celery

- `retrain_forecast_model(tenant_id)`
- `periodic_forecast_retrain` — Mondays 03:30 UTC

## Evaluation Metrics

- **MAE / RMSE** on demand units
- **R²** coefficient
- **MAPE %**
- **demand_score_mae** on 0–100 scale
