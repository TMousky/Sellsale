import os


class Config:
    def __init__(self):
        # BigCommerce
        self.BC_STORE_HASH = os.getenv("BIGCOMMERCE_STORE_HASH")
        self.BC_CLIENT_ID = os.getenv("BIGCOMMERCE_CLIENT_ID")
        self.BC_CLIENT_SECRET = os.getenv("BIGCOMMERCE_CLIENT_SECRET")
        self.BC_ACCESS_TOKEN = os.getenv("BIGCOMMERCE_ACCESS_TOKEN")

        # Bot settings
        self.MARKUP_MULTIPLIER = float(os.getenv("MARKUP_MULTIPLIER", "2.5"))
        self.MIN_RATING = float(os.getenv("MIN_RATING", "4.5"))
        self.MIN_ORDERS = int(os.getenv("MIN_ORDERS", "100"))
        self.MAX_PRODUCTS = int(os.getenv("MAX_PRODUCTS", "200"))
        self.PRODUCT_CATEGORIES = os.getenv(
            "PRODUCT_CATEGORIES",
            "pet supplies,dog toys,cat accessories,pet grooming,pet beds,fish tank,reptile supplies,bird cage"
        ).split(",")

        self._validate()

    def _validate(self):
        missing = []
        if not self.BC_STORE_HASH:
            missing.append("BIGCOMMERCE_STORE_HASH")
        if not self.BC_ACCESS_TOKEN:
            missing.append("BIGCOMMERCE_ACCESS_TOKEN")
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
