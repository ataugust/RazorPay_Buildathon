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
        "sku": "MON-000",
        "name": "HP P24 G5 Monitor",
        "brand": "HP",
        "model": "P24 G5",
        "category": "MONITOR",
        "selling_price_rupees": 13800,
        "cost_price_rupees": 10500,
        "stock_quantity": 75,
        "display_inches": 23.8,
        "resolution": "Full HD",
        "is_overstock": False,
        "is_active": True,
    },
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
    # Expanded production-like inventory
    {"sku": "LAP-007", "name": "Apple MacBook Air M3", "brand": "Apple", "model": "MacBook Air M3", "category": "LAPTOP", "selling_price_rupees": 114900, "cost_price_rupees": 97000, "stock_quantity": 32, "ram_gb": 16, "storage_gb": 512, "storage_type": "SSD", "display_inches": 13.6, "operating_system": "macOS", "is_overstock": False, "is_active": True},
    {"sku": "LAP-008", "name": "Dell Inspiron 14", "brand": "Dell", "model": "Inspiron 14", "category": "LAPTOP", "selling_price_rupees": 74900, "cost_price_rupees": 59000, "stock_quantity": 65, "cpu_brand": "Intel", "cpu_tier": "i5", "cpu_generation": "13th Gen", "ram_gb": 16, "storage_gb": 512, "storage_type": "SSD", "display_inches": 14.0, "operating_system": "Windows 11", "is_overstock": False, "is_active": True},
    {"sku": "LAP-009", "name": "ASUS Vivobook 15", "brand": "ASUS", "model": "Vivobook 15", "category": "LAPTOP", "selling_price_rupees": 58900, "cost_price_rupees": 46000, "stock_quantity": 90, "cpu_brand": "AMD", "cpu_tier": "Ryzen 5", "ram_gb": 16, "storage_gb": 512, "storage_type": "SSD", "display_inches": 15.6, "operating_system": "Windows 11", "is_overstock": False, "is_active": True},
    {"sku": "LAP-010", "name": "Acer Chromebook Plus", "brand": "Acer", "model": "Chromebook Plus", "category": "LAPTOP", "selling_price_rupees": 39900, "cost_price_rupees": 31000, "stock_quantity": 140, "ram_gb": 8, "storage_gb": 256, "storage_type": "SSD", "display_inches": 14.0, "operating_system": "ChromeOS", "is_overstock": True, "is_active": True},
    {"sku": "MON-003", "name": "Samsung Essential 24 Monitor", "brand": "Samsung", "model": "Essential 24", "category": "MONITOR", "selling_price_rupees": 11900, "cost_price_rupees": 8800, "stock_quantity": 180, "display_inches": 24.0, "resolution": "Full HD", "is_overstock": False, "is_active": True},
    {"sku": "MON-004", "name": "Acer EK220Q Monitor", "brand": "Acer", "model": "EK220Q", "category": "MONITOR", "selling_price_rupees": 8900, "cost_price_rupees": 6500, "stock_quantity": 210, "display_inches": 21.5, "resolution": "Full HD", "is_overstock": True, "is_active": True},
    {"sku": "MON-005", "name": "BenQ GW2790 Monitor", "brand": "BenQ", "model": "GW2790", "category": "MONITOR", "selling_price_rupees": 15900, "cost_price_rupees": 11800, "stock_quantity": 95, "display_inches": 27.0, "resolution": "Full HD", "is_overstock": False, "is_active": True},
    {"sku": "MON-006", "name": "Dell UltraSharp U2724D", "brand": "Dell", "model": "U2724D", "category": "MONITOR", "selling_price_rupees": 46900, "cost_price_rupees": 37500, "stock_quantity": 28, "display_inches": 27.0, "resolution": "QHD", "is_overstock": False, "is_active": True},
    {"sku": "ACC-003", "name": "Logitech M331 Wireless Mouse", "brand": "Logitech", "model": "M331", "category": "ACCESSORY", "selling_price_rupees": 1499, "cost_price_rupees": 900, "stock_quantity": 420, "is_overstock": False, "is_active": True},
    {"sku": "ACC-004", "name": "Logitech K380 Bluetooth Keyboard", "brand": "Logitech", "model": "K380", "category": "ACCESSORY", "selling_price_rupees": 3295, "cost_price_rupees": 2200, "stock_quantity": 240, "is_overstock": False, "is_active": True},
    {"sku": "ACC-005", "name": "Dell Pro Wireless Keyboard", "brand": "Dell", "model": "KM5221W", "category": "ACCESSORY", "selling_price_rupees": 2799, "cost_price_rupees": 1750, "stock_quantity": 310, "is_overstock": True, "is_active": True},
    {"sku": "ACC-006", "name": "Jabra Evolve2 40 Headset", "brand": "Jabra", "model": "Evolve2 40", "category": "ACCESSORY", "selling_price_rupees": 12900, "cost_price_rupees": 8900, "stock_quantity": 85, "is_overstock": False, "is_active": True},
    {"sku": "ACC-007", "name": "Logitech C920 HD Webcam", "brand": "Logitech", "model": "C920", "category": "ACCESSORY", "selling_price_rupees": 7495, "cost_price_rupees": 4900, "stock_quantity": 160, "is_overstock": False, "is_active": True},
    {"sku": "ACC-008", "name": "Samsung T7 1TB Portable SSD", "brand": "Samsung", "model": "T7", "category": "ACCESSORY", "selling_price_rupees": 9499, "cost_price_rupees": 6900, "stock_quantity": 130, "storage_gb": 1024, "storage_type": "SSD", "is_overstock": False, "is_active": True},
    {"sku": "ACC-009", "name": "Anker 65W USB-C Charger", "brand": "Anker", "model": "Nano II 65W", "category": "ACCESSORY", "selling_price_rupees": 4499, "cost_price_rupees": 2800, "stock_quantity": 275, "is_overstock": True, "is_active": True},
    {"sku": "LAP-NEO-001", "name": "Apple MacBook Neo", "brand": "Apple", "model": "MacBook Neo", "category": "LAPTOP", "selling_price_rupees": 75000, "cost_price_rupees": 64000, "stock_quantity": 80, "cpu_brand": "Apple", "cpu_tier": "M2", "ram_gb": 16, "storage_gb": 512, "storage_type": "SSD", "display_inches": 13.6, "operating_system": "macOS", "is_overstock": False, "is_active": True},
    {"sku": "ACC-DEMO-MOUSE", "name": "ASC Wireless Mouse", "brand": "ASC", "model": "AirClick", "category": "ACCESSORY", "selling_price_rupees": 1500, "cost_price_rupees": 450, "stock_quantity": 400, "is_overstock": True, "is_active": True},
]

def seed_products(update_existing=True):
    db = SessionLocal()
    try:
        created_count = 0
        updated_count = 0

        for item_data in PRODUCTS_SEED:
            sku = item_data["sku"]
            existing = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()

            if existing:
                if update_existing:
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
