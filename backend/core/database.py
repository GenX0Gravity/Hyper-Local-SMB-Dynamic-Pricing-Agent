from sqlmodel import SQLModel, create_engine, Session
from backend.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=True, # Echo SQL queries for debugging
    connect_args=connect_args
)

def init_db():
    # Import all models to ensure they are registered before creating tables
    from backend.models.tenant import Tenant
    from backend.models.user import User
    from backend.models.product import Product
    from backend.models.rule import PricingRule
    from backend.models.signal import DemandSignal
    from backend.models.recommendation import Recommendation, RecommendationAudit
    from backend.models.sales_history import SalesHistory
    from backend.models.forecast_model import ForecastModelRun
    from backend.models.analytics_snapshot import AnalyticsSnapshot

    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
