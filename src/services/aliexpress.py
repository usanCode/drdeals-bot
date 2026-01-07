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

    def _call_link_generate(self, source: str) -> dict:
        params = {
            "app_key": self.app_key,
            "method": "aliexpress.affiliate.link.generate",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "sign_method": "md5",
            "v": "2.0",
            "partner_id": "top-autopilot",
            "promotion_link_type": "0",
            "source_values": source,
            "tracking_id": self.tracking_id,
        }
        params["sign"] = self._sign(params)
        return self.session.post(ALI_ENDPOINT, data=params, timeout=8).json()

    def generate_link(self, url: str) -> str:
        if not url:
            return ""

        source = url.strip()

        # Retry loop for ApiCallLimit
        for attempt in range(1, 4):  # 3 attempts
            try:
                data = self._call_link_generate(source)

                if "error_response" in data:
                    err = data.get("error_response", {})
                    code = err.get("code")
                    msg = err.get("msg", "")

                    if code == "ApiCallLimit":
                        # Increasing wait each attempt
                        wait = 1.7 if attempt == 1 else (2.2 if attempt == 2 else 2.8)
                        log.warning(
                            "Link.generate rate limited (attempt %s), sleeping %ss. msg=%s source=%s",
                            attempt, wait, msg, source
                        )
                        time.sleep(wait)
                        continue

                    log.warning("Link.generate error code=%s msg=%s source=%s body=%s", code, msg, source, data)
                    return ""

                resp = data.get("aliexpress_affiliate_link_generate_response")
                if not resp:
                    log.warning("Link.generate unexpected response keys=%s source=%s body=%s", list(data.keys()), source, data)
                    return ""

                resp_result = resp.get("resp_result", {})
                result = resp_result.get("result") or {}
                promo_links = (result.get("promotion_links") or {}).get("promotion_link") or []
                if not promo_links:
                    log.warning("Link.generate no promotion_link source=%s result=%s", source, result)
                    return ""

                link = promo_links[0]
                final = link.get("promotion_short_link") or link.get("promotion_link") or ""
                return final

            except Exception as e:
                log.warning("Link generate failed attempt %s for %s: %s", attempt, source, e)
                time.sleep(0.6)

        # After retries, give up (no non-affiliate fallback)
        return ""
