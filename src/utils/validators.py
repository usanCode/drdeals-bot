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

BAD_WORDS = ["screw", "repair", "tool", "adapter", "connector", "pipe", "hair clipper", "trimmer", "parts"]

def is_valid_product(product: dict, query_he: str) -> bool:
    title_lower = (product.get("product_title") or "").lower()
    if any(b in title_lower for b in BAD_WORDS):
        return False

    for key, valid_list in VALIDATORS.items():
        if key in query_he:
            if not any(v in title_lower for v in valid_list):
                return False

    return True
