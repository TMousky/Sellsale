import time
import schedule
import logging
from datetime import datetime
from config import Config
from product_manager import ProductManager
from order_manager import OrderManager
from inventory_monitor import InventoryMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s SELLSALE %(message)s",
    datefmt="%H:%M:%S,%f"
)
log = logging.getLogger(__name__)

cfg = Config()
product_mgr = ProductManager(cfg)
order_mgr = OrderManager(cfg)
inventory_mgr = InventoryMonitor(cfg)


def print_status():
    stats = product_mgr.get_stats()
    log.info(
        f"Balance:N/A | Products:{stats['total']} | "
        f"Orders:{order_mgr.fulfilled_count} | Revenue:${order_mgr.total_revenue:.2f}"
    )


def run_product_finder():
    log.info("Scanning AliExpress for winning pet products...")
    added = product_mgr.find_and_list_products(limit=5)
    log.info(f"Added {added} new products to Shopify")


def run_order_fulfillment():
    log.info("Checking for unfulfilled orders...")
    fulfilled = order_mgr.process_pending_orders()
    log.info(f"Fulfilled {fulfilled} orders")


def run_inventory_check():
    log.info("Checking inventory levels...")
    removed = inventory_mgr.remove_out_of_stock()
    updated = inventory_mgr.sync_stock_levels()
    log.info(f"Removed {removed} OOS products | Updated {updated} stock levels")


def run_price_monitor():
    log.info("Updating prices based on supplier costs...")
    updated = product_mgr.refresh_prices()
    log.info(f"Updated prices for {updated} products")


if __name__ == "__main__":
    log.info("=" * 50)
    log.info("SELLSALE STARTING UP")
    log.info("=" * 50)

    run_product_finder()
    run_order_fulfillment()
    run_inventory_check()
    print_status()

    schedule.every(30).minutes.do(run_product_finder)
    schedule.every(5).minutes.do(run_order_fulfillment)
    schedule.every(1).hours.do(run_inventory_check)
    schedule.every(2).hours.do(run_price_monitor)
    schedule.every(10).minutes.do(print_status)

    log.info("Scheduler running. SellSale is live.")

    while True:
        schedule.run_pending()
        time.sleep(30)
