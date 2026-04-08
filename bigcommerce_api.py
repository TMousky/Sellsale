import requests
import logging
import time

log = logging.getLogger(__name__)


class BigCommerceAPI:
    def __init__(self, cfg):
        self.base_url = f"https://api.bigcommerce.com/stores/{cfg.BC_STORE_HASH}/v2"
        self.base_url_v3 = f"https://api.bigcommerce.com/stores/{cfg.BC_STORE_HASH}/v3"
        self.headers = {
            "X-Auth-Token": cfg.BC_ACCESS_TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, url, params=None):
        r = requests.get(url, headers=self.headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, url, data):
        r = requests.post(url, headers=self.headers, json=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def _put(self, url, data):
        r = requests.put(url, headers=self.headers, json=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def _delete(self, url):
        r = requests.delete(url, headers=self.headers, timeout=15)
        r.raise_for_status()

    def get_all_products(self):
        products = []
        page = 1
        while True:
            data = self._get(
                f"{self.base_url_v3}/catalog/products",
                params={"limit": 250, "page": page}
            )
            batch = data.get("data", [])
            products.extend(batch)
            meta = data.get("meta", {}).get("pagination", {})
            if page >= meta.get("total_pages", 1):
                break
            page += 1
        return products

    def create_product(self, title, description, price, compare_price, images, brand, categories):
        payload = {
            "name": title,
            "type": "physical",
            "description": description,
            "price": round(price, 2),
            "sale_price": round(price, 2),
            "retail_price": round(compare_price, 2),
            "weight": 1,
            "is_visible": True,
            "brand_name": brand,
            "categories": categories or [18],
            "images": [
                {"image_url": url, "is_thumbnail": i == 0}
                for i, url in enumerate(images[:5])
            ],
        }
        result = self._post(f"{self.base_url_v3}/catalog/products", payload)
        return result.get("data")

    def update_product_price(self, product_id, new_price):
        payload = {"price": round(new_price, 2), "sale_price": round(new_price, 2)}
        return self._put(
            f"{self.base_url_v3}/catalog/products/{product_id}",
            payload
        )

    def delete_product(self, product_id):
        try:
            self._delete(f"{self.base_url_v3}/catalog/products/{product_id}")
            return True
        except Exception as e:
            log.warning(f"Failed to delete product {product_id}: {e}")
            return False

    def set_product_inventory(self, product_id, quantity):
        payload = {
            "inventory_level": quantity,
            "inventory_tracking": "product",
        }
        return self._put(
            f"{self.base_url_v3}/catalog/products/{product_id}",
            payload
        )

    def get_unfulfilled_orders(self):
        try:
            r = requests.get(
                f"{self.base_url}/orders",
                headers=self.headers,
                params={"status_id": 11, "limit": 50},
                timeout=15,
            )
            if r.status_code == 204 or not r.text.strip():
                return []
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            log.warning(f"No orders yet: {e}")
            return []

    def get_order_products(self, order_id):
        data = self._get(f"{self.base_url}/orders/{order_id}/products")
        return data if isinstance(data, list) else []

    def get_order_shipping_address(self, order_id):
        data = self._get(f"{self.base_url}/orders/{order_id}/shipping_addresses")
        return data[0] if data else {}

    def mark_order_shipped(self, order_id, tracking_number=None):
        payload = {"status_id": 2}
        self._put(f"{self.base_url}/orders/{order_id}", payload)

        if tracking_number:
            order_products = self.get_order_products(order_id)
            items = [{"order_product_id": p["id"], "quantity": p["quantity"]}
                     for p in order_products]
            shipment_payload = {
                "tracking_number": tracking_number,
                "shipping_provider": "aliexpress",
                "items": items,
            }
            try:
                self._post(f"{self.base_url}/orders/{order_id}/shipments", shipment_payload)
            except Exception as e:
                log.warning(f"Shipment record failed: {e}")
