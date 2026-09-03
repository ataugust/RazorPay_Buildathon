from sqlmodel import Session, select
from app.db.database import engine, init_db
from app.domain.models import Product, MerchantPolicy

def seed_data():
    init_db()
    with Session(engine) as session:
        # Check if already seeded
        existing_product = session.exec(select(Product)).first()
        if existing_product:
            print("Database already contains product data.")
            return

        # Seed Merchant Inventory
        products = [
            Product(
                sku="LAP-LEN-001",
                name="Lenovo IdeaPad Slim 3",
                category="Laptops",
                selling_price_paise=13500000,  # ₹1,35,000 in paise
                cost_price_paise=10000000,     # ₹1,00,000 in paise
                stock=50,
                discount_allowed=True,
            ),
            Product(
                sku="LAP-LEN-002",
                name="Lenovo ThinkPad E14",
                category="Laptops",
                selling_price_paise=15000000,  # ₹1,50,000 in paise
                cost_price_paise=11500000,     # ₹1,15,000 in paise
                stock=30,
                discount_allowed=True,
            ),
            Product(
                sku="ACC-BAG-001",
                name="Lenovo Laptop Backpack (Overstock)",
                category="Accessories",
                selling_price_paise=300000,    # ₹3,000 in paise
                cost_price_paise=80000,        # ₹800 in paise (overstock high margin)
                stock=200,
                discount_allowed=True,
            ),
            Product(
                sku="ACC-MOU-001",
                name="Wireless Ergonomic Mouse",
                category="Accessories",
                selling_price_paise=150000,    # ₹1,500 in paise
                cost_price_paise=40000,        # ₹400 in paise
                stock=150,
                discount_allowed=True,
            ),
        ]

        for p in products:
            session.add(p)

        # Seed Default Merchant Policy
        policy = MerchantPolicy(
            name="default_policy",
            min_margin_percent=15.0,  # Min 15% profit margin requirement
            allow_discounts=True,
            allow_bundles=True,
            max_discount_percent=20.0, # Max 20% discount allowed
        )
        session.add(policy)

        session.commit()
        print("Database successfully seeded with inventory and policy!")

if __name__ == "__main__":
    seed_data()
