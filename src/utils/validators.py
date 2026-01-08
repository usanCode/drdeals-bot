import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Set

# Global exclusions (still useful as a first filter)
GLOBAL_EXCLUDE = {
    "screw", "repair", "tool", "adapter", "connector",
    "pipe", "hair clipper", "trimmer", "parts",
}

@dataclass(frozen=True)
class CategoryRule:
    strong_any: Set[str] = field(default_factory=set)
    weak_any: Set[str] = field(default_factory=set)
    exclude_any: Set[str] = field(default_factory=set)
    min_strong_hits: int = 1

CATEGORY_RULES: Dict[str, CategoryRule] = {
    "מעיל": CategoryRule(
        strong_any={"coat", "jacket", "parka", "outerwear", "blazer"},
        exclude_any={"button", "zipper", "replacement", "patch"},
    ),
    "רחפן": CategoryRule(
        strong_any={"drone", "quadcopter", "uav"},
        exclude_any={"propeller", "props", "battery", "charger", "replacement", "spare"},
    ),
    "שעון": CategoryRule(
        strong_any={"watch", "smartwatch"},
        weak_any={"fitness tracker", "tracker"},
        exclude_any={"band", "strap", "replacement", "bracelet", "buckle", "link"},
    ),
    "אוזניות": CategoryRule(
        strong_any={"headphone", "earphone", "earbuds", "headset"},
        exclude_any={"case", "replacement", "ear tips", "tips", "adapter", "cable"},
    ),
    "תיק": CategoryRule(
        strong_any={"bag", "handbag", "backpack", "purse"},
        weak_any={"tote", "crossbody", "satchel"},
        exclude_any={"strap", "replacement", "insert", "organizer"},
    ),
    "נעליים": CategoryRule(
        strong_any={"shoe", "shoes", "sneaker", "sneakers", "boot", "boots", "sandal", "sandals", "heels"},
        exclude_any={"laces", "insole", "insoles", "replacement", "polish", "cleaner"},
    ),
    "mini pc": CategoryRule(
        strong_any={
            "mini pc", "minipc", "desktop", "computer",
            "intel", "amd", "ryzen", "celeron", "pentium", "core",
            "windows", "linux",
            "ddr4", "ddr5", "ram", "memory", "ssd", "nvme",
            "n100", "n95", "n97", "i3", "i5", "i7",
            "barebone", "barebones",
        },
        exclude_any={
            "screwdriver", "repair tool", "tool kit",
            "microphone", "lavalier",
            "endoscope", "borescope", "inspection",
            "mouse", "keyboard",
            "lamp", "light", "bulb",
            "screen", "monitor", "display", "secondary screen",
            "camera", "usb camera",
        },
        min_strong_hits=2,   # <-- THIS is the important change
    ),
"מגפיים": CategoryRule(
    strong_any={
        "boot", "boots",
        "ankle boot", "ankle boots",
        "chelsea boot", "chelsea boots",
        "combat boot", "combat boots",
        "winter boot", "winter boots",
        "snow boot", "snow boots",
        "leather boot", "leather boots",
        "platform boot", "platform boots",
    },
    exclude_any={
        # covers & protection
        "boot cover", "shoe cover", "rain cover", "waterproof cover",
        "overshoe", "over shoe",

        # add-ons & accessories
        "anti slip", "anti-skid", "traction", "cleat", "grip",
        "shoe spike", "ice grip",
        "insole", "insoles",
        "laces",
        "polish", "cleaner",
        "repair", "repair kit",
        "protector", "guard",

        # tools / unrelated
        "dryer", "heater",
    },
    min_strong_hits=1,
),


}

# Keep COLORS because other modules import it and expect .items()
COLORS = {
    "שחור": "black",
    "לבן": "white",
    "אדום": "red",
    "כחול": "blue",
    "ירוק": "green",
    "צהוב": "yellow",
    "אפור": "gray",
    "ורוד": "pink",
    "סגול": "purple",
    "כתום": "orange",
    "חום": "brown",
}

def _normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[\u2019\u2018`´’]", "'", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _word_hit(text: str, term: str) -> bool:
    term = _normalize_text(term)
    if not term:
        return False
    if " " in term:
        return term in text
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None

def _count_hits(text: str, terms: Iterable[str]) -> int:
    return sum(1 for t in terms if _word_hit(text, t))

def _rating_ok(raw_rating) -> bool:
    if raw_rating is None:
        return False
    try:
        if isinstance(raw_rating, str) and "%" in raw_rating:
            percent = float(raw_rating.replace("%", "").strip())
            return percent >= 84.0
        stars = float(raw_rating)
        return stars >= 4.2
    except (ValueError, TypeError):
        return False

# Light hardware detection: only used to apply a basic "PC-like title" requirement
HARDWARE_QUERY_TRIGGERS = {
    "mini pc", "minipc", "pc", "computer", "desktop", "laptop",
    "מחשב", "מחשב קטן", "מיני מחשב", "מחשב נייח",
}

# Minimal hardware "strong" words: like strong_any for other categories
HARDWARE_STRONG_ANY = {
    "mini pc", "minipc", "computer", "desktop", "laptop",
    # keep "pc" but be careful with boundary match, _word_hit handles that
    "pc",
}

def _is_hardware_query(qnorm: str) -> bool:
    return any(t in qnorm for t in HARDWARE_QUERY_TRIGGERS)

def is_valid_product(product: dict, query_he: str) -> bool:
    title_raw = product.get("product_title") or ""
    title = _normalize_text(title_raw)
    if not title:
        return False

    query_he = query_he or ""
    qnorm = _normalize_text(query_he)

    # Detect a mini PC query (Hebrew or English)
    is_mini_pc_query = any(k in qnorm for k in {"mini pc", "minipc", "מיני מחשב", "מחשב קטן"})

    # Rating gate: keep as you had it (mini pc does not require rating)
    if not is_mini_pc_query:
        if not _rating_ok(product.get("evaluate_rate")):
            return False

    # Global exclude: keep as you had it (do not apply for mini pc)
    if not is_mini_pc_query:
        if any(_word_hit(title, w) for w in GLOBAL_EXCLUDE):
            return False

    # Mini PC handled via CATEGORY_RULES (dictionary driven)
    if is_mini_pc_query:
        rule = CATEGORY_RULES.get("mini pc")
        if rule is None:
            return True

        if any(_word_hit(title, w) for w in rule.exclude_any):
            return False

        hits = _count_hits(title, rule.strong_any)

        # explicit mini pc title gets a pass (light mode)
        if ("mini pc" in title) or ("minipc" in title):
            return True

        # otherwise require the threshold
        if hits < rule.min_strong_hits:
            return False

        return True


    # Existing category rules (unchanged)
    for he_key, rule in CATEGORY_RULES.items():
        if he_key in query_he:
            if any(_word_hit(title, w) for w in rule.exclude_any):
                return False
            hits = _count_hits(title, rule.strong_any)

            # If title explicitly says "mini pc" / "minipc", allow with 1 hit
            if ("mini pc" in title) or ("minipc" in title):
                return True

            # Otherwise require the normal threshold (2)
            if hits < rule.min_strong_hits:
                return False


    return True
