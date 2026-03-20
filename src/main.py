import logging
import os
import time
import requests
import telebot
from threading import Thread
from flask import Flask, jsonify

from src.config import settings
from src.utils.logging_setup import setup_logging
from src.services.aliexpress import AliExpressClient
from src.bot.handlers import register_handlers


app = Flask(__name__)


@app.route("/")
def root() -> str:
    return "deals-finder-bot is online"


@app.route("/health")
def health() -> object:
    return jsonify(status="ok")


def run_polling(bot) -> None:
    log = logging.getLogger("main")
    log.info("Starting Telegram polling loop...")

    while True:
        try:
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=10,
            )
        except requests.exceptions.ReadTimeout:
            log.warning("Telegram long polling timed out, retrying...")
            time.sleep(2)
        except requests.exceptions.ConnectionError as e:
            log.warning("Telegram connection error: %s. Retrying...", e)
            time.sleep(5)
        except Exception as e:
            log.exception("Unexpected polling error: %s", e)
            time.sleep(5)


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

    register_handlers(
        bot,
        ali,
        page_size=settings.page_size,
        min_sale_price=settings.min_sale_price,
    )

    log.info("Bot is initialized")

    polling_thread = Thread(target=run_polling, args=(bot,), daemon=True)
    polling_thread.start()

    port = int(os.environ.get("PORT", 5000))
    log.info("Starting Flask app on port %s", port)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
