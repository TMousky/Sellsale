import logging
import json
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


class InventoryMonitor:
    def __init__(self, cfg):
        self.ali = AliExpressAPI(cfg)
        self.bc = BigCommerceAPI(cfg)

    def remove_out_of_stock(self):
        db = _load_db()
        removed = 0
        to_remove = []

        for ali_id, record in db.items():
            try:
                detail = self.ali.get_product_detail(ali_id)
                if detail is None or detail.get("sale_price", 0) == 0:
                    log.info(f"  OOS: {record['title'][:50]} — removing")
                    if self.bc.delete_product(record["bc_product_id"]):
                        to_remove.append(ali_id)
                        removed += 1
                time.sleep(0.5)
            except Exception as e:
                log.warning(f"  Check failed for {ali_id}: {e}")

        for ali_id in to_remove:
            del db[ali_id]
        if to_remove:
            _save_db(db)

        return removed

    def sync_stock_levels(self):
        db = _load_db()
        updated = 0

        for ali_id, record in db.items():
            try:
                detail = self.ali.get_product_detail(ali_id)
                if not detail:
                    continue
                qty = 999 if detail["sale_price"] > 0 else 0
                self.bc.set_product_inventory(record["bc_product_id"], qty)
                updated += 1
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"  Stock sync failed for {ali_id}: {e}")

        return updated
