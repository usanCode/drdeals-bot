import logging
import time
import json
from datetime import datetime
from pathlib import Path

from telebot import TeleBot, types

from src.services.translate import safe_translate
from src.utils.validators import COLORS, is_valid_product
from src.utils.collage import create_collage
from src.services.aliexpress import AliExpressClient

log = logging.getLogger(__name__)

# Logs directory under project
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
BOT_LOG_PATH = LOGS_DIR / "drdeals_bot_activity.log"


def log_bot_event(event: dict) -> None:
    """Append one JSON line to the bot activity log."""
    try:
        event["ts"] = datetime.utcnow().isoformat() + "Z"
        with open(BOT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        log.warning("Failed writing bot activity log: %s", e)


def rating_to_stars(raw_rating) -> str:
    """Normalize rating to stars for display."""
    if raw_rating is None:
        return "?"

    try:
        # Percent like "88.6%"
        if isinstance(raw_rating, str) and "%" in raw_rating:
            pct = float(raw_rating.replace("%", "").strip())
            stars = pct / 20.0
            return f"{stars:.1f}"

        # Stars like "4.6"
        stars = float(raw_rating)
        return f"{stars:.1f}"

    except (ValueError, TypeError):
        return "?"


def register_handlers(
    bot: TeleBot,
    ali: AliExpressClient,
    page_size: int,
    min_sale_price: int,
) -> None:

    @bot.message_handler(func=lambda m: True)
    def handler(m):
        if not getattr(m, "text", None):
            return
        if not m.text.startswith("חפש לי"):
            return

        query_he = m.text.replace("חפש לי", "").strip()
        if not query_he:
            bot.reply_to(m, "תני לי מה לחפש אחרי 'חפש לי'.")
            return

        user = getattr(m, "from_user", None)

        log_bot_event({
            "type": "search",
            "query": query_he,
            "chat_id": getattr(m.chat, "id", None),
            "user_id": getattr(user, "id", None),
            "username": getattr(user, "username", None),
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
        })

        try:
            msg = bot.reply_to(
                m,
                f"🔎 קיבלתי: '{query_he}'.\n📡 מתחבר לשרתים..."
            )
            bot.send_chat_action(m.chat.id, "typing")
            time.sleep(1.5)

            color_en = ""
            for h, e in COLORS.items():
                if h in query_he:
                    color_en = e
                    break

            base_en = safe_translate(query_he, "en")
            extra = "Fashion Elegant" if "מעיל" in query_he else ""
            final_query = f"{base_en} {color_en} {extra}".strip()

            bot.edit_message_text(
                f"📥 מחפש: {base_en}...",
                m.chat.id,
                msg.message_id,
            )

            products = ali.product_query(
                final_query,
                page_size=page_size,
                min_sale_price=min_sale_price,
            )

            time.sleep(1.0)

            bot.edit_message_text(
                "🧹 מסנן תוצאות...",
                m.chat.id,
                msg.message_id,
            )

            valid_products = [
                p for p in products if is_valid_product(p, query_he)
            ]

            if not valid_products:
                log_bot_event({
                    "type": "no_results_after_filter",
                    "query": query_he,
                    "chat_id": m.chat.id,
                    "user_id": getattr(user, "id", None),
                    "candidates_count": len(products),
                })

                bot.edit_message_text(
                    "🛑 לא מצאתי תוצאות טובות אחרי סינון.",
                    m.chat.id,
                    msg.message_id,
                )
                return

            bot.edit_message_text(
                "✍️ מכין קישורים...",
                m.chat.id,
                msg.message_id,
            )

            max_items = 4
            candidates = valid_products[:25]
            picked: list[tuple[dict, str]] = []
            progress_updated = False


            for p in candidates:
                short_link = p.get("promotion_short_link")
                if short_link:
                    link = short_link
                    source = "promotion_short_link"
                else:
                    raw = p.get("product_detail_url", "")
                    link = ali.generate_link(raw)
                    source = "generate_link"

                time.sleep(0.35)

                if not link:
                    log_bot_event({
                        "type": "link_failed",
                        "query": query_he,
                        "product_id": p.get("product_id"),
                        "source": source,
                    })
                    continue

                picked.append((p, link))
                if not progress_updated:
                    bot.edit_message_text(
                        "⏳ עוד רגע והכול מוכן ✨",
                        m.chat.id,
                        msg.message_id,
                    )
                    progress_updated = True

                log_bot_event({
                    "type": "link_generated",
                    "query": query_he,
                    "product_id": p.get("product_id"),
                    "affiliate_link": link,
                    "source": source,
                    "evaluate_rate": p.get("evaluate_rate"),
                })

                if len(picked) >= max_items:
                    break

            if not picked:
                bot.delete_message(m.chat.id, msg.message_id)
                bot.send_message(
                    m.chat.id,
                    "🛑 לא הצלחתי לייצר קישורי אפיליאייט כרגע. נסי שוב עוד רגע.",
                )
                return

            images: list[str] = []
            text = "🛍️ **הבחירות המובילות עבורך:**\n\n"
            kb = types.InlineKeyboardMarkup()

            for i, (p, link) in enumerate(picked):

                title_raw = p.get("product_title", "")
                price = p.get("target_sale_price") or p.get("sale_price") or "?"

                rating = rating_to_stars(p.get("evaluate_rate"))
                orders = p.get("lastest_volume") or p.get("last_volume")

                img_url = p.get("product_main_image_url")
                if img_url:
                    images.append(img_url)

                title_he = safe_translate(title_raw, "iw")
                title_clean = " ".join(title_he.split()[:9])

                text += f"{i+1}. 🥇 {title_clean}\n"

                line = f"💰 מחיר: {price}₪ | ⭐ {rating}"
                if orders is not None and str(orders).strip() != "":
                    line += f" | 🛒 {orders}"
                text += line + "\n"

                safe_link = link.replace("_", r"\_")
                text += f"{safe_link}\n\n"

                kb.add(types.InlineKeyboardButton(f"מוצר {i+1}", url=link))


            bot.delete_message(m.chat.id, msg.message_id)

            if images:
                try:
                    collage = create_collage(images, session=ali.session)
                    bot.send_photo(
                        m.chat.id,
                        collage,
                        caption=text,
                        parse_mode="Markdown",
                        reply_markup=kb,
                    )
                    return
                except Exception as e:
                    log.warning("Collage send failed: %s", e)

            bot.send_message(
                m.chat.id,
                text,
                parse_mode="Markdown",
                reply_markup=kb,
                disable_web_page_preview=True,
            )

        except Exception as e:
            log.exception("Handler error: %s", e)
            try:
                bot.send_message(m.chat.id, "שגיאה זמנית.")
            except Exception:
                pass
