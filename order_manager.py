import logging
import json
import os
import time
from bigcommerce_api import BigCommerceAPI

log = logging.getLogger(__name__)
ORDERS_DB = "orders_db.json"


def _load_orders():
    if os.path.exists(ORDERS_DB):
        with open(ORDERS_DB) as f:
            return json.load(f)
    return {}


def _save_orders(db):
    with open(ORDERS_DB, "w") as f:
        json.dump(db, f, indent=2)


class OrderManager:
    def __init__(self, cfg):
        self.bc = BigCommerceAPI(cfg)
        self.orders_db = _load_orders()
        self.fulfilled_count = sum(
            1 for o in self.orders_db.values() if o.get("status") == "fulfilled"
        )
        self.total_revenue = sum(
            float(o.get("revenue", 0)) for o in self.orders_db.values()
        )

    def process_pending_orders(self):
        unfulfilled = self.bc.get_unfulfilled_orders()
        fulfilled = 0

        for order in unfulfilled:
            order_id = str(order["id"])
            if order_id in self.orders_db:
                continue

            shipping = self.bc.get_order_shipping_address(order["id"])
            products = self.bc.get_order_products(order["id"])

            log.info(
                f"  Processing order #{order['id']} "
                f"({len(products)} item(s)) for {shipping.get('first_name', 'customer')}"
            )

            for item in products:
                ali_id = self._get_ali_id(item["product_id"])
                log.info(
                    f"    → Fulfill: item {ali_id or item['product_id']} x{item['quantity']} "
                    f"to {shipping.get('city')}, {shipping.get('country_iso2')}"
                )

            try:
                self.bc.mark_order_shipped(order["id"])
                revenue = float(order.get("total_inc_tax", 0))
                self.orders_db[order_id] = {
                    "order_id": order_id,
                    "status": "fulfilled",
                    "revenue": revenue,
                }
                _save_orders(self.orders_db)
                self.fulfilled_count += 1
                self.total_revenue += revenue
                fulfilled += 1
                log.info(f"    ✅ Order #{order['id']} fulfilled | Revenue: ${revenue:.2f}")
            except Exception as e:
                log.error(f"    Failed to fulfill order #{order['id']}: {e}")

            time.sleep(1)

        return fulfilled

    def _get_ali_id(self, bc_product_id):
        if os.path.exists("products_db.json"):
            with open("products_db.json") as f:
                db = json.load(f)
            for ali_id, record in db.items():
                if record["bc_product_id"] == bc_product_id:
                    return ali_id
        return None
