import logging

log = logging.getLogger(__name__)

try:
    from deep_translator import GoogleTranslator
    _HAS_TRANSLATOR = True
except Exception:
    _HAS_TRANSLATOR = False

def safe_translate(text: str, target: str = "en") -> str:
    if not _HAS_TRANSLATOR:
        return text
    try:
        return GoogleTranslator(source="auto", target=target).translate(text)
    except Exception as e:
        log.warning("Translate failed: %s", e)
        return text
