import logging
import time
from telebot import TeleBot, types

from src.services.translate import safe_translate
from src.utils.validators import COLORS, is_valid_product
from src.utils.collage import create_collage
from src.services.aliexpress import AliExpressClient

log = logging.getLogger(__name__)

def register_handlers(bot: TeleBot, ali: AliExpressClient, page_size: int, min_sale_price: int) -> None:
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

        try:
            msg = bot.reply_to(m, f"🔎 קיבלתי: '{query_he}'.\n📡 מתחבר לשרתים...")
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

            bot.edit_message_text(f"📥 מחפש: {base_en}...", m.chat.id, msg.message_id)
            products = ali.product_query(final_query, page_size=page_size, min_sale_price=min_sale_price)
            time.sleep(1.0)

            bot.edit_message_text("🧹 מסנן תוצאות...", m.chat.id, msg.message_id)
            valid_products = [p for p in products if is_valid_product(p, query_he)]
            time.sleep(0.8)

            if not valid_products:
                bot.edit_message_text("🛑 לא מצאתי תוצאות טובות אחרי סינון.", m.chat.id, msg.message_id)
                return

            bot.edit_message_text("✍️ מכין קישורים...", m.chat.id, msg.message_id)

            top_4 = valid_products[:4]
            images: list[str] = []
            text = "🛍️ **הבחירות המובילות עבורך:**\n\n"
            kb = types.InlineKeyboardMarkup()

            for i, p in enumerate(top_4):
                title_raw = p.get("product_title", "")
                price = p.get("target_sale_price") or p.get("sale_price") or "?"
                rating = p.get("evaluate_rate", "4.8")
                orders = p.get("last_volume", "100+")

                raw_link = p.get("product_detail_url", "")
                link = ali.generate_link(raw_link)
                if not link:
                    continue

                img_url = p.get("product_main_image_url")
                if img_url:
                    images.append(img_url)

                title_he = safe_translate(title_raw, "iw")
                title_clean = " ".join(title_he.split()[:9])

                text += f"{i+1}. 🥇 {title_clean}\n"
                text += f"💰 מחיר: {price}₪ | ⭐ {rating} | 🛒 {orders}\n"
                safe_link = link.replace("_", r"\_")
                text += f"{safe_link}\n\n"
                kb.add(types.InlineKeyboardButton(f"מוצר {i+1}", url=link))

            bot.delete_message(m.chat.id, msg.message_id)

            if images:
                try:
                    collage = create_collage(images, session=ali.session)
                    bot.send_photo(m.chat.id, collage, caption=text, parse_mode="Markdown", reply_markup=kb)
                    
                    return
                except Exception as e:
                    log.warning("Collage send failed: %s", e)

            bot.send_message(m.chat.id, text, parse_mode="Markdown", reply_markup=kb)

        except Exception as e:
            log.exception("Handler error: %s", e)
            try:
                bot.send_message(m.chat.id, "שגיאה זמנית.")
            except Exception:
                pass
