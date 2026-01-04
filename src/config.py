import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _get(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return val

@dataclass(frozen=True)
class Settings:
    bot_token: str = _get("BOT_TOKEN")
    ali_app_key: str = _get("ALI_APP_KEY")
    ali_app_secret: str = _get("ALI_APP_SECRET")
    tracking_id: str = os.getenv("TRACKING_ID", "DrDeals")

    ship_to_country: str = os.getenv("SHIP_TO_COUNTRY", "IL")
    target_currency: str = os.getenv("TARGET_CURRENCY", "ILS")
    min_sale_price: int = int(os.getenv("MIN_SALE_PRICE", "20"))
    page_size: int = int(os.getenv("PAGE_SIZE", "50"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
