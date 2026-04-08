import json
import logging
import os
import time
from aliexpress import AliExpressAPI
from bigcommerce_api import BigCommerceAPI

log = logging.getLogger(__name__)
DB_FILE = "products_db.json"


def _load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            return json.load(f)
    return {}


def _save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


class ProductManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ali = AliExpressAPI(cfg)
        self.bc = BigCommerceAPI(cfg)
        self.markup = cfg.MARKUP_MULTIPLIER
        self.db = _load_db()

    def find_and_list_products(self, limit=5):
        if len(self.db) >= self.cfg.MAX_PRODUCTS:
            log.info(f"At max products ({self.cfg.MAX_PRODUCTS}), skipping.")
            return 0

        keywords = self.cfg.PRODUCT_CATEGORIES
        winners = self.ali.find_winning_products(keywords)
        log.info(f"Found {len(winners)} potential products")

        added = 0
        for item in winners:
            if added >= limit:
                break
            if item["item_id"] in self.db:
                continue

            detail = self.ali.get_product_detail(item["item_id"])
            if not detail or not detail["images"]:
                continue

            shopify_price = round(detail["sale_price"] * self.markup, 2)
            compare_price = round(shopify_price * 1.3, 2)
            description = self._build_description(detail)

            try:
                product = self.bc.create_product(
                    title=self._clean_title(detail["title"]),
                    description=description,
                    price=shopify_price,
                    compare_price=compare_price,
                    images=detail["images"][:5],
                    brand=detail["store_name"],
                    categories=[],
                )
                if product:
                    self.db[item["item_id"]] = {
                        "bc_product_id": product["id"],
                        "ali_price": detail["sale_price"],
                        "bc_price": shopify_price,
                        "title": product["name"],
                    }
                    _save_db(self.db)
                    added += 1
                    log.info(
                        f"  Listed: {product['name'][:50]} "
                        f"| AliEx: ${detail['sale_price']:.2f} → Store: ${shopify_price:.2f}"
                    )
                time.sleep(0.5)
except Exception as e:
                log.error(f"  Failed to list product: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    log.error(f"  BigCommerce error details: {e.response.text}")

        return added

    def refresh_prices(self):
        updated = 0
        for ali_id, record in list(self.db.items()):
            try:
                detail = self.ali.get_product_detail(ali_id)
                if not detail:
                    continue
                new_ali_price = detail["sale_price"]
                if abs(new_ali_price - record["ali_price"]) > 0.10:
                    new_bc_price = round(new_ali_price * self.markup, 2)
                    self.bc.update_product_price(record["bc_product_id"], new_bc_price)
                    self.db[ali_id]["ali_price"] = new_ali_price
                    self.db[ali_id]["bc_price"] = new_bc_price
                    _save_db(self.db)
                    updated += 1
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"Price refresh failed for {ali_id}: {e}")
        return updated

    def get_stats(self):
        return {"total": len(self.db)}

    def _clean_title(self, title):
        return title[:80].strip()

    def _build_description(self, detail):
        return f"""
<div style="font-family: sans-serif; max-width: 600px;">
  <h2>{self._clean_title(detail['title'])}</h2>
  <p><strong>⭐ Rating:</strong> {detail.get('rating', 'N/A')}/5 
     &nbsp;|&nbsp; <strong>✅ Orders:</strong> {detail.get('orders', 0):,}+</p>
  <p>Premium pet product sourced from a top-rated supplier. Perfect for your furry, scaly, or feathered friend!</p>
  <ul>
    <li>Fast shipping</li>
    <li>30-day return policy</li>
    <li>Satisfaction guaranteed</li>
  </ul>
</div>
"""
