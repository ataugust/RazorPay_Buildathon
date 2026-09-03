import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.product import Product

PRODUCTS_SEED = [
    # Laptops (6)
    {
        "sku": "LAP-001",
        "name": "Lenovo IdeaPad Pro 16",
        "brand": "Lenovo",
        "model": "IdeaPad Pro 16",
        "category": "LAPTOP",
        "selling_price_rupees": 125000,
        "cost_price_rupees": 100000,
        "stock_quantity": 60,
        "cpu_brand": "Intel",
        "cpu_tier": "i5",
        "cpu_generation": "13th Gen",
        "ram_gb": 16,
        "storage_gb": 512,
        "storage_type": "SSD",
        "display_inches": 16.0,
        "operating_system": "Windows 11 Pro",
        "is_overstock": False,
        "is_active": True,
    },
    {
        "sku": "LAP-002",
        "name": "HP ProBook 450",
        "brand": "HP",
        "model": "ProBook 450",
        "category": "LAPTOP",
        "selling_price_rupees": 112000,
        "cost_price_rupees": 90000,
        "stock_quantity": 80,
        "cpu_brand": "Intel",
        "cpu_tier": "i5",
        "cpu_generation": "13th Gen",
        "ram_gb": 16,
        "storage_gb": 512,
        "storage_type": "SSD",
        "display_inches": 15.6,
        "operating_system": "Windows 11 Pro",
        "is_overstock": False,
        "is_active": True,
    },
    {
        "sku": "LAP-003",
        "name": "Dell Latitude 5450",
        "brand": "Dell",
        "model": "Latitude 5450",
        "category": "LAPTOP",
        "selling_price_rupees": 145000,
        "cost_price_rupees": 118000,
        "stock_quantity": 30,
        "cpu_brand": "Intel",
        "cpu_tier": "i7",
        "cpu_generation": "13th Gen",
        "ram_gb": 16,
        "storage_gb": 1024,
        "storage_type": "SSD",
        "display_inches": 14.0,
        "operating_system": "Windows 11 Pro",
        "is_overstock": False,
        "is_active": True,
    },
    {
        "sku": "LAP-004",
        "name": "Acer Aspire Business",
        "brand": "Acer",
        "model": "Aspire Business",
        "category": "LAPTOP",
        "selling_price_rupees": 90000,
        "cost_price_rupees": 72000,
        "stock_quantity": 100,
        "cpu_brand": "Intel",
        "cpu_tier": "i5",
        "cpu_generation": "12th Gen",
        "ram_gb": 8,
        "storage_gb": 512,
        "storage_type": "SSD",
        "display_inches": 15.6,
        "operating_system": "Windows 11",
        "is_overstock": False,
        "is_active": True,
    },
    {
        "sku": "LAP-005",
        "name": "Lenovo ThinkPad E16",
        "brand": "Lenovo",
        "model": "ThinkPad E16",
        "category": "LAPTOP",
        "selling_price_rupees": 135000,
        "cost_price_rupees": 108000,
        "stock_quantity": 20,
        "cpu_brand": "Intel",
        "cpu_tier": "i5",
        "cpu_generation": "13th Gen",
        "ram_gb": 16,
        "storage_gb": 1024,
        "storage_type": "SSD",
        "display_inches": 16.0,
        "operating_system": "Windows 11 Pro",
        "is_overstock": False,
        "is_active": True,
    },
    {
        "sku": "LAP-006",
        "name": "ASUS ExpertBook B1",
        "brand": "ASUS",
        "model": "ExpertBook B1",
        "category": "LAPTOP",
        "selling_price_rupees": 105000,
        "cost_price_rupees": 84000,
        "stock_quantity": 50,
        "cpu_brand": "Intel",
        "cpu_tier": "i5",
        "cpu_generation": "13th Gen",
        "ram_gb": 16,
        "storage_gb": 512,
        "storage_type": "SSD",
        "display_inches": 14.0,
        "operating_system": "Windows 11 Pro",
        "is_overstock": False,
        "is_active": True,
    },

    # Monitors (2)
    {
        "sku": "MON-001",
        "name": "Dell Professional Monitor",
        "brand": "Dell",
        "model": "Professional Monitor",
        "category": "MONITOR",
        "selling_price_rupees": 28000,
        "cost_price_rupees": 21000,
        "stock_quantity": 40,
        "display_inches": 27.0,
        "resolution": "QHD",
        "is_overstock": False,
        "is_active": True,
    },
    {
        "sku": "MON-002",
        "name": "LG Office Monitor",
        "brand": "LG",
        "model": "Office Monitor",
        "category": "MONITOR",
        "selling_price_rupees": 18000,
        "cost_price_rupees": 12500,
        "stock_quantity": 120,
        "display_inches": 24.0,
        "resolution": "Full HD",
        "is_overstock": False,
        "is_active": True,
    },

    # Accessories (2)
    {
        "sku": "ACC-001",
        "name": "Wireless Mouse",
        "brand": "Generic",
        "model": "Wireless Mouse",
        "category": "ACCESSORY",
        "selling_price_rupees": 3000,
        "cost_price_rupees": 700,
        "stock_quantity": 500,
        "is_overstock": True,
        "is_active": True,
    },
    {
        "sku": "ACC-002",
        "name": "USB-C Hub",
        "brand": "Generic",
        "model": "USB-C Hub",
        "category": "ACCESSORY",
        "selling_price_rupees": 4000,
        "cost_price_rupees": 1500,
        "stock_quantity": 250,
        "is_overstock": True,
        "is_active": True,
    },
]

def seed_products():
    db = SessionLocal()
    try:
        created_count = 0
        updated_count = 0

        for item_data in PRODUCTS_SEED:
            sku = item_data["sku"]
            existing = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()

            if existing:
                for key, val in item_data.items():
                    setattr(existing, key, val)
                updated_count += 1
            else:
                product = Product(**item_data)
                db.add(product)
                created_count += 1

        db.commit()
        print(f"Seeding completed successfully! ({created_count} created, {updated_count} updated)")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_products()
