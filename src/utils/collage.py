import io
import logging
from PIL import Image, ImageDraw, ImageFont
import requests

log = logging.getLogger(__name__)

def create_collage(image_urls: list[str], session: requests.Session) -> io.BytesIO:
    imgs: list[Image.Image] = []

    for u in image_urls[:4]:
        try:
            resp = session.get(u, timeout=6)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB").resize((500, 500))
            imgs.append(img)
        except Exception as e:
            log.warning("Image fetch failed: %s", e)
            imgs.append(Image.new("RGB", (500, 500), "white"))

    while len(imgs) < 4:
        imgs.append(Image.new("RGB", (500, 500), "white"))

    canvas = Image.new("RGB", (1000, 1000), "white")
    canvas.paste(imgs[0], (0, 0))
    canvas.paste(imgs[1], (500, 0))
    canvas.paste(imgs[2], (0, 500))
    canvas.paste(imgs[3], (500, 500))

    draw = ImageDraw.Draw(canvas)

    # ---- FONT (Windows-safe bold) ----
    font_path = r"C:\Windows\Fonts\arialbd.ttf"
    try:
        font = ImageFont.truetype(font_path, 60)
        log.info("Loaded font: %s", font_path)
    except Exception as e:
        log.warning("Font load failed, using default: %s", e)
        font = ImageFont.load_default()

    # ---- NUMBER POSITIONS ----
    positions = [(30, 30), (530, 30), (30, 530), (530, 530)]

    for i, (x, y) in enumerate(positions):
        shadow_offset = 6

        # shadow
        draw.ellipse(
            (
                x + shadow_offset,
                y + shadow_offset,
                x + 100 + shadow_offset,
                y + 100 + shadow_offset,
            ),
            fill="#000000"
        )

        # main badge
        draw.ellipse(
            (x, y, x + 100, y + 100),
            fill="#111111",
            outline="white",
            width=4
        )

        # number
        draw.text(
            (x + 36, y + 18),
            str(i + 1),
            fill="white",
            font=font
        )

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=85)
    out.seek(0)
    return out
