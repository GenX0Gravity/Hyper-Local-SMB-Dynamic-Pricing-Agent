import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from backend.core.config import settings
from backend.core.database import init_db, engine
from backend.api.v1 import auth, store, products, rules, recommendations, signals, analytics, forecast, weather, events, pricing, whatsapp
from backend.api.v1 import orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(store.router, prefix=f"{settings.API_V1_STR}/store", tags=["store settings"])
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["products"])
app.include_router(rules.router, prefix=f"{settings.API_V1_STR}/rules", tags=["pricing rules"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recommendations", tags=["recommendations"])
app.include_router(signals.router, prefix=f"{settings.API_V1_STR}/signals", tags=["signals"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(forecast.router, prefix=f"{settings.API_V1_STR}/forecast", tags=["demand forecasting"])
app.include_router(weather.router, prefix=f"{settings.API_V1_STR}/weather", tags=["weather intelligence"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/events", tags=["event intelligence"])
app.include_router(pricing.router, prefix=f"{settings.API_V1_STR}/pricing", tags=["dynamic pricing"])
app.include_router(whatsapp.router, prefix=f"{settings.API_V1_STR}/whatsapp", tags=["whatsapp agent"])
app.include_router(orchestrator.router, prefix=f"{settings.API_V1_STR}/orchestrator", tags=["orchestrator"])

@app.get("/")
def read_root():
    return {"message": "PricePulse AI API is online", "docs": "/docs"}

def seed_demo_data(session: Session):
    """
    Seeds a sample cafe tenant, product catalog, sales, and pricing rules
    if no tenants are currently defined in the DB.
    """
    from backend.models.tenant import Tenant
    from backend.models.user import User
    from backend.models.product import Product
    from backend.models.rule import PricingRule
    from backend.models.sales_history import SalesHistory
    from backend.core.security import get_password_hash

    # Check if there are existing tenants
    existing_tenant = session.exec(select(Tenant)).first()
    if existing_tenant:
        logger.info("Database already contains data. Skipping demo seed.")
        return

    logger.info("Seeding demo store data (The Daily Brew Cafe)...")

    # 1. Create Tenant
    demo_tenant = Tenant(
        name="The Daily Brew Cafe",
        business_type="cafe",
        latitude=40.7128,  # New York coordinates
        longitude=-74.0060,
        timezone="America/New_York",
        whatsapp_phone="+15550199",
        whatsapp_enabled=True,
        currency="USD"
    )
    session.add(demo_tenant)
    session.flush()

    # 2. Create Owner User (username: demo@pricepulse.ai, password: password123)
    demo_user = User(
        tenant_id=demo_tenant.id,
        email="demo@pricepulse.ai",
        hashed_password=get_password_hash("password123"),
        full_name="Alex Mercer",
        role="owner",
        is_active=True
    )
    session.add(demo_user)

    # 3. Create Product Catalog
    coffee_products = [
        Product(
            tenant_id=demo_tenant.id,
            sku="COF-LAT-LG",
            name="Vanilla Latte (Large)",
            description="Signature espresso with steamed milk and vanilla syrup",
            category="Beverages",
            cost_price=1.20,
            base_price=4.50,
            current_price=4.50,
            min_price=3.50,
            max_price=6.50,
            stock_qty=200
        ),
        Product(
            tenant_id=demo_tenant.id,
            sku="COF-ESP-DB",
            name="Double Espresso Shot",
            description="Rich, concentrated dark roast espresso",
            category="Beverages",
            cost_price=0.40,
            base_price=3.00,
            current_price=3.00,
            min_price=2.00,
            max_price=4.50,
            stock_qty=500
        ),
        Product(
            tenant_id=demo_tenant.id,
            sku="BAK-CRO-PL",
            name="Butter Croissant",
            description="Flaky, fresh-baked classic butter croissant",
            category="Pastries",
            cost_price=0.80,
            base_price=3.75,
            current_price=3.75,
            min_price=2.50,
            max_price=5.50,
            stock_qty=45
        ),
        Product(
            tenant_id=demo_tenant.id,
            sku="COF-CLD-BRW",
            name="Cold Brew Coffee",
            description="Slow-steeped iced cold brew blend",
            category="Beverages",
            cost_price=0.70,
            base_price=4.25,
            current_price=4.25,
            min_price=3.00,
            max_price=6.00,
            stock_qty=150
        )
    ]
    for p in coffee_products:
        session.add(p)
    session.flush()

    # 4. Create Pricing Rules
    rules = [
        PricingRule(
            tenant_id=demo_tenant.id,
            name="Rainy Day Coffee Booster",
            rule_type="weather",
            conditions={"weather": "Rainy", "category": "Beverages"},
            adjustment_type="percentage",
            adjustment_value=15.0, # Increase prices by 15% when it rains (hot comfort drinks spike in demand)
            is_active=True
        ),
        PricingRule(
            tenant_id=demo_tenant.id,
            name="Afternoon Slump Happy Hour",
            rule_type="time_of_day",
            conditions={"hour_start": 14, "hour_end": 16, "days_of_week": [0,1,2,3,4]}, # Mon-Fri, 2-4 PM
            adjustment_type="fixed",
            adjustment_value=-0.75, # $0.75 off during low traffic afternoon hours
            is_active=True
        ),
        PricingRule(
            tenant_id=demo_tenant.id,
            name="Pastry Clearance Sale",
            rule_type="inventory",
            conditions={"stock_below": 10, "category": "Pastries"},
            adjustment_type="percentage",
            adjustment_value=-20.0, # Clear stock at 20% discount if stock drops low
            is_active=False
        ),
        PricingRule(
            tenant_id=demo_tenant.id,
            name="Concert Crowd Surge Pricing",
            rule_type="event",
            conditions={"attendance_above": 3000, "radius_km": 1.5},
            adjustment_type="percentage",
            adjustment_value=20.0, # 20% markup during local concerts (high foot traffic)
            is_active=True
        )
    ]
    for r in rules:
        session.add(r)

    # 5. Populate some sales history to render mock statistics
    # 3 days of historical sales
    from datetime import datetime, timezone, timedelta
    for index, prod in enumerate(coffee_products):
        for days_back in range(1, 4):
            sale_time = datetime.now(timezone.utc) - timedelta(days=days_back, hours=days_back * 2)
            session.add(
                SalesHistory(
                    tenant_id=demo_tenant.id,
                    product_id=prod.id,
                    quantity=12 + (index * 4) + days_back,
                    price_sold=prod.base_price,
                    sold_at=sale_time
                )
            )
            
    session.commit()
    logger.info("Demo store database seeding completed.")

@app.on_event("startup")
def on_startup():
    logger.info("Initializing database schemas...")
    init_db()
    with Session(engine) as session:
        seed_demo_data(session)
