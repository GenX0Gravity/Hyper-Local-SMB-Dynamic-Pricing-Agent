"""Tests for Event Intelligence Engine."""

from datetime import datetime, timezone

import pytest

from backend.services.event_intelligence.classifier import EventClassifier
from backend.services.event_intelligence.pipeline import EventDataPipeline
from backend.services.event_intelligence.rules import EventRulesEngine
from backend.services.event_intelligence.scoring import EventImpactScorer
from backend.services.event_intelligence.schemas import (
    EventCategory,
    EventSource,
    RawEventRecord,
)


def test_classifier_ipl():
    clf = EventClassifier()
    record = RawEventRecord(
        external_id="1",
        name="IPL Final 2026 Live Screening Downtown",
        raw_category="sports",
        attendance_est=15000,
        source=EventSource.MOCK,
    )
    category, confidence = clf.classify(record)
    assert category == EventCategory.IPL_MATCH
    assert confidence >= 0.9


def test_classifier_durga_puja():
    clf = EventClassifier()
    record = RawEventRecord(
        external_id="2",
        name="Durga Puja Pandal Opening Ceremony",
        source=EventSource.NEWSAPI,
    )
    category, _ = clf.classify(record)
    assert category == EventCategory.DURGA_PUJA


def test_impact_scorer_high_attendance_nearby():
    scorer = EventImpactScorer()
    record = RawEventRecord(
        external_id="3",
        name="IPL Match Day",
        raw_category="sports",
        attendance_est=20000,
        distance_km=0.5,
        start_at=datetime.now(timezone.utc),
        source=EventSource.PREDICTHQ,
        trend_interest=80.0,
        news_sentiment="positive",
    )
    classified = scorer.build_classified(record)
    assert classified.impact_score >= 40.0
    assert classified.category == EventCategory.IPL_MATCH


def test_aggregate_impact_multiple_events():
    scorer = EventImpactScorer()
    events = []
    for name, att in [("IPL Match", 20000), ("Local Fair", 800)]:
        record = RawEventRecord(
            external_id=name,
            name=name,
            attendance_est=att,
            distance_km=1.0,
            source=EventSource.MOCK,
        )
        events.append(scorer.build_classified(record))
    aggregate = scorer.aggregate_impact(events)
    assert aggregate >= events[0].impact_score


def test_rules_engine_critical_surge():
    scorer = EventImpactScorer()
    record = RawEventRecord(
        external_id="4",
        name="IPL Playoffs",
        attendance_est=50000,
        distance_km=0.3,
        start_at=datetime.now(timezone.utc),
        source=EventSource.MOCK,
        trend_interest=95.0,
    )
    classified = scorer.build_classified(record)
    aggregate = scorer.aggregate_impact([classified])
    report = EventRulesEngine().evaluate(
        events=[classified],
        aggregate_impact_score=aggregate,
        category_summary=[],
    )
    assert report.aggregate_impact_score == aggregate
    assert len(report.events) == 1


@pytest.mark.asyncio
async def test_pipeline_mock_run():
    pipeline = EventDataPipeline()
    events, stats = await pipeline.run(22.5726, 88.3639, radius_km=2.0)
    assert stats["raw_count"] > 0
    assert len(events) > 0
    assert all(0 <= e.impact_score <= 100 for e in events)
    assert stats["deduped_count"] <= stats["raw_count"]
