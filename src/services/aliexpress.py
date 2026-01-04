import hashlib
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

log = logging.getLogger(__name__)

ALI_ENDPOINT = "https://api-sg.aliexpress.com/sync"

class AliExpressClient:
    def __init__(self, app_key: str, app_secret: str, tracking_id: str, ship_to_country: str, target_currency: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.tracking_id = tracking_id
        self.ship_to_country = ship_to_country
        self.target_currency = target_currency

        self.session = requests.Session()
        retry = Retry(connect=3, read=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)

    def _sign(self, params: dict) -> str:
        s = self.app_secret + "".join(f"{k}{v}" for k, v in sorted(params.items())) + self.app_secret
        return hashlib.md5(s.encode()).hexdigest().upper()

    def product_query(self, keywords: str, page_size: int = 50, min_sale_price: int = 20, sort: str = "LAST_VOLUME_DESC") -> list[dict]:
        params = {
            "app_key": self.app_key,
            "method": "aliexpress.affiliate.product.query",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "sign_method": "md5",
            "v": "2.0",
            "partner_id": "top-autopilot",
            "keywords": keywords,
            "target_currency": self.target_currency,
            "ship_to_country": self.ship_to_country,
            "sort": sort,
            "page_size": str(page_size),
            "min_sale_price": str(min_sale_price),
        }
        params["sign"] = self._sign(params)

        try:
            r = self.session.post(ALI_ENDPOINT, data=params, timeout=10)
            data = r.json()
        except Exception as e:
            log.warning("Ali product query failed: %s", e)
            return []

        key = "aliexpress_affiliate_product_query_response"
        if key not in data:
            return []

        try:
            products = data[key]["resp_result"]["result"]["products"]["product"]
            return products if isinstance(products, list) else [products]
        except Exception:
            return []

    def generate_link(self, url: str) -> str:
        if not url:
            return ""
        clean = url.split("?")[0]
        params = {
            "app_key": self.app_key,
            "method": "aliexpress.affiliate.link.generate",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "sign_method": "md5",
            "v": "2.0",
            "partner_id": "top-autopilot",
            "promotion_link_type": "0",
            "source_values": clean,
            "tracking_id": self.tracking_id,
        }
        params["sign"] = self._sign(params)

        try:
            r = self.session.post(ALI_ENDPOINT, data=params, timeout=8).json()
            res = r["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]
            link = res["promotion_links"]["promotion_link"][0]
            final = link.get("promotion_short_link") or link.get("promotion_link")
            return final or clean
        except Exception as e:
            log.warning("Link generate failed: %s", e)
            return clean
