import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, BeforeValidator
from typing_extensions import Annotated
from dotenv import load_dotenv

load_dotenv()


def any_http_url_list_validator(v: str | List[str]) -> List[str]:
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip() for item in v.split(",")]
    return v

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    PROJECT_NAME: str = "PricePulse AI"
    API_V1_STR: str = "/api/v1"
    
    # Security & Auth
    SECRET_KEY: str = "SUPER_SECRET_SECURITY_JWT_KEY_SIGNING_12345" # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: Annotated[
        List[str], BeforeValidator(any_http_url_list_validator)
    ] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "pricepulse"
    
    @property
    def DATABASE_URL(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Settings (Cache & Broker)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    @property
    def REDIS_CACHE_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        
    @property
    def REDIS_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # External APIs
    OPENWEATHER_API_KEY: str = ""

    # Weather intelligence
    WEATHER_CACHE_TTL_CURRENT: int = 600       # 10 min — current conditions
    WEATHER_CACHE_TTL_FORECAST: int = 1800     # 30 min — 5-day/3h forecast
    WEATHER_CACHE_TTL_INTELLIGENCE: int = 300  # 5 min — full report per tenant
    WEATHER_HEAVY_RAIN_MM_1H: float = 7.0      # mm/hr threshold for heavy rain
    WEATHER_CHAI_DEMAND_BOOST_PCT: float = 22.0
    WEATHER_INDOOR_SEATING_BOOST_PCT: float = 28.0
    WEATHER_HEATWAVE_TEMP_C: float = 32.0
    WEATHER_HIGH_WIND_MS: float = 12.0
    PREDICTHQ_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # LangGraph / LLM (optional — agent falls back to rule engine)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AGENT_MAX_RETRIES: int = 3
    AGENT_SIGNAL_CACHE_TTL_SECONDS: int = 900

    # Demand forecasting (XGBoost)
    FORECAST_MODEL_DIR: str = "data/models/forecasting"
    FORECAST_MIN_TRAINING_ROWS: int = 48
    FORECAST_TRAIN_TEST_SPLIT: float = 0.2
    FORECAST_RETRAIN_DAYS: int = 7
    
    # Twilio / WhatsApp Integration
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"  # Twilio Sandbox number by default
    TWILIO_ENABLED: bool = False

settings = Settings()
