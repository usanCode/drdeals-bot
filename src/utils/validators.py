VALIDATORS = {
    "מעיל": ["coat", "jacket", "parka", "outerwear", "blazer"],
    "רחפן": ["drone", "quadcopter", "uav"],
    "שעון": ["watch", "smartwatch", "band"],
    "אוזניות": ["headphone", "earphone", "earbuds", "headset"],
    "תיק": ["bag", "handbag", "wallet", "backpack", "purse"],
    "נעליים": ["shoe", "sneaker", "boot", "sandal", "heels"],
}

COLORS = {
    "שמנת": "Beige", "בז": "Beige", "קרם": "Beige", "חול": "Khaki",
    "לבן": "White", "שחור": "Black", "אדום": "Red",
    "כחול": "Blue", "ירוק": "Green", "ורוד": "Pink", "חום": "Brown",
}

BAD_WORDS = [
    "screw", "repair", "tool", "adapter", "connector",
    "pipe", "hair clipper", "trimmer", "parts"
]


def is_valid_product(product: dict, query_he: str) -> bool:
    title_lower = (product.get("product_title") or "").lower()

    # Reject bad words
    if any(b in title_lower for b in BAD_WORDS):
        return False

    # Keyword / category validation
    for key, valid_list in VALIDATORS.items():
        if key in query_he:
            if not any(v in title_lower for v in valid_list):
                return False

    # Rating validation
    raw_rating = product.get("evaluate_rate")
    if raw_rating is None:
        return False

    try:
        # Case 1: percentage rating like "88.6%"
        if isinstance(raw_rating, str) and "%" in raw_rating:
            percent = float(raw_rating.replace("%", "").strip())
            if percent < 84.0:  # 4.2 stars * 20
                return False

        # Case 2: star rating like "4.6"
        else:
            stars = float(raw_rating)
            if stars < 4.2:
                return False

    except (ValueError, TypeError):
        return False

    return True
