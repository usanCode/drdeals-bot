import logging
import telebot

from src.config import settings
from src.utils.logging_setup import setup_logging
from src.services.aliexpress import AliExpressClient
from src.bot.handlers import register_handlers

def main() -> None:
    setup_logging(settings.log_level)
    log = logging.getLogger("main")

    bot = telebot.TeleBot(settings.bot_token, parse_mode=None)

    ali = AliExpressClient(
        app_key=settings.ali_app_key,
        app_secret=settings.ali_app_secret,
        tracking_id=settings.tracking_id,
        ship_to_country=settings.ship_to_country,
        target_currency=settings.target_currency,
    )

    register_handlers(bot, ali, page_size=settings.page_size, min_sale_price=settings.min_sale_price)

    log.info("Bot is running...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

if __name__ == "__main__":
    main()
