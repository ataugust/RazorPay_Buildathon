"""Deterministic category, identity, and hardware matching across the catalog."""
import re
from sqlalchemy import select
from app.db.models.product import Product


def tokens(value):
    value = re.sub(r"\bmice\b", "mouse", (value or "").lower())
    value = re.sub(r"\bnotebooks?\b", "laptop", value)
    return [word.rstrip("s") for word in re.findall(r"[a-z0-9]+", value)]


def cpu_matches(product, requirement):
    if not requirement:
        return True
    required = re.sub(r"\s+", "", requirement.lower()).replace("ryzen", "r")
    actual = re.sub(r"\s+", "", (product.cpu_tier or "").lower()).replace("ryzen", "r")
    if required.startswith("r") and (product.cpu_brand or "").lower() not in {"amd", "ryzen"}:
        return False
    if required.startswith("i") and (product.cpu_brand or "").lower() not in {"intel"}:
        return False
    return bool(actual and actual[0] == required[0] and actual[1:].isdigit() and required[1:].isdigit() and int(actual[1:]) >= int(required[1:]))


def specs_match(product, specs):
    return (
        (not specs.get("min_ram_gb") or (product.ram_gb or 0) >= specs["min_ram_gb"])
        and (not specs.get("min_storage_gb") or (product.storage_gb or 0) >= specs["min_storage_gb"])
        and cpu_matches(product, specs.get("min_cpu_tier"))
    )


def find_products(db, query, specs=None):
    words = tokens(query)
    ignored = {"any", "a", "an", "the", "computer", "with", "of"}
    words = [word for word in words if word not in ignored]
    products = db.scalars(select(Product).where(Product.is_active.is_(True))).all()
    matches = []
    for product in products:
        identity = set(tokens(" ".join(str(v or "") for v in [product.name, product.brand, product.model, product.sku, product.category])))
        if words and all(word in identity for word in words) and specs_match(product, specs or {}):
            matches.append(product)
    return sorted(matches, key=lambda p: (p.selling_price_rupees, p.sku))
