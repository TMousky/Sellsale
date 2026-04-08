import requests
import logging
import time
import random
import json
import re

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.aliexpress.com",
    }


class AliExpressAPI:
    def __init__(self, cfg):
        self.min_rating = cfg.MIN_RATING
        self.min_orders = cfg.MIN_ORDERS
        self.session = requests.Session()

    def search_products(self, keyword, page=1):
        try:
            url = "https://www.aliexpress.com/wholesale"
            params = {
                "SearchText": keyword,
                "page": page,
                "sortType": "total_tranpro_desc",
                "currency": "USD",
                "language": "en",
            }
            r = self.session.get(url, headers=_get_headers(), params=params, timeout=20)
            html = r.text
            return self._extract_products_from_html(html)
        except Exception as e:
            log.error(f"Search error for '{keyword}': {e}")
            return []

    def _extract_products_from_html(self, html):
        items = []
        try:
            match = re.search(r'"mods"\s*:\s*\{.*?"itemList"\s*:\s*\{"content"\s*:\s*(\[.+?\])\s*[,}]', html, re.DOTALL)
            if match:
                try:
                    content = json.loads(match.group(1))
                    for raw in content:
                        item = self._parse_item(raw)
                        if item["item_id"] and item["sale_price"] > 0:
                            items.append(item)
                    return items
                except Exception:
                    pass

            ids = re.findall(r'"productId"\s*:\s*"?(\d+)"?', html)
            prices = re.findall(r'"minPrice"\s*:\s*"?([\d.]+)"?', html)
            titles = re.findall(r'"title"\s*:\s*"([^"]{10,120})"', html)
            images = re.findall(r'(https://ae0[12]\.alicdn\.com/kf/[^"\'>\s]+\.jpg)', html)

            for i, item_id in enumerate(ids[:20]):
                items.append({
                    "item_id": item_id,
                    "title": titles[i] if i < len(titles) else f"Pet Product {item_id}",
                    "sale_price": float(prices[i]) if i < len(prices) else 0,
                    "image": images[i] if i < len(images) else "",
                    "orders": 150,
                    "store_rating": 4.5,
                })
        except Exception as e:
            log.warning(f"HTML extraction error: {e}")
        return items

    def get_product_detail(self, item_id):
        try:
            url = f"https://www.aliexpress.com/item/{item_id}.html"
            r = self.session.get(url, headers=_get_headers(), timeout=20)
            html = r.text

            match = re.search(r'window\.runParams\s*=\s*\{(.*?)\};\s*</script>', html, re.DOTALL)
            if not match:
                match = re.search(r'"data"\s*:\s*(\{.+?"priceModule".+?\})\s*[,;]', html, re.DOTALL)

            if match:
                try:
                    data = json.loads("{" + match.group(1) + "}")
                    result = self._parse_detail(data, item_id, html)
                    if result and result["sale_price"] > 0:
                        return result
                except Exception:
                    pass

            return self._parse_detail_from_html(html, item_id)

        except Exception as e:
            log.error(f"Detail error for {item_id}: {e}")
            return None

    def _parse_detail(self, data, item_id, html):
        price = float(
            data.get("priceModule", {}).get("minActivityAmount", {}).get("value", 0)
            or data.get("priceModule", {}).get("minAmount", {}).get("value", 0)
            or 0
        )
        title = (
            data.get("titleModule", {}).get("subject", "")
            or data.get("subject", "")
            or f"Pet Product {item_id}"
        )
        images = data.get("imageModule", {}).get("imagePathList", []) or self._extract_images(html)
        feedback = data.get("feedbackModule", {})

        return {
            "title": title,
            "sale_price": price,
            "images": images[:10],
            "store_name": data.get("storeModule", {}).get("storeName", "AliExpress Seller"),
            "store_rating": float(feedback.get("tradeScore", 4.5) or 4.5),
            "orders": int(feedback.get("tradeCount", 150) or 150),
            "rating": float(feedback.get("averageStar", 4.5) or 4.5),
        }

    def _parse_detail_from_html(self, html, item_id):
        try:
            title_match = re.search(r'<title>([^|<]+)', html)
            price_match = re.search(r'US\s*\$\s*([\d.]+)', html)
            images = self._extract_images(html)

            title = title_match.group(1).strip() if title_match else f"Pet Product {item_id}"
            price = float(price_match.group(1)) if price_match else 0

            if price == 0 or not images:
                return None

            return {
                "title": title,
                "sale_price": price,
                "images": images,
                "store_name": "AliExpress Seller",
                "store_rating": 4.5,
                "orders": 150,
                "rating": 4.5,
            }
        except Exception as e:
            log.error(f"HTML detail parse error: {e}")
            return None

    def _extract_images(self, html):
        images = []
        match = re.search(r'"imagePathList"\s*:\s*(\[[^\]]+\])', html)
        if match:
            try:
                images = json.loads(match.group(1))
                return images[:10]
            except Exception:
                pass
        images = re.findall(r'(https://ae0[12]\.alicdn\.com/kf/[^"\'>\s]+\.jpg)', html)
        return list(set(images))[:10]

    def _parse_item(self, raw):
        try:
            prices = raw.get("prices", {})
            sale_price = float(
                prices.get("salePrice", {}).get("minPrice", 0)
                or prices.get("minPrice", 0)
                or 0
            )
            orders_raw = raw.get("tradeDesc", "0")
            orders = int(re.sub(r'[^\d]', '', str(orders_raw).split()[0]) or 0)
            return {
                "item_id": str(raw.get("productId", raw.get("itemId", ""))),
                "title": raw.get("title", ""),
                "sale_price": sale_price,
                "image": raw.get("imageUrl", ""),
                "orders": orders,
                "store_rating": float(raw.get("starRating", 4.5) or 4.5),
            }
        except Exception:
            return {"item_id": "", "title": "", "sale_price": 0, "image": "", "orders": 0, "store_rating": 0}

    def find_winning_products(self, keywords, min_rating=None, min_orders=None):
        min_orders = min_orders or self.min_orders
        winners = []
        seen = set()

        for kw in keywords:
            log.info(f"  Searching: '{kw.strip()}'")
            results = self.search_products(kw.strip())
            for item in results:
                if (
                    item["item_id"]
                    and item["item_id"] not in seen
                    and item["sale_price"] > 0
                    and item["orders"] >= min_orders
                ):
                    seen.add(item["item_id"])
                    winners.append(item)
            time.sleep(random.uniform(2.0, 4.0))

        winners.sort(key=lambda x: x["orders"], reverse=True)
        return winners
