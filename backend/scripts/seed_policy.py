import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.merchant_policy import MerchantPolicy

DEFAULT_POLICIES = [
    {
        "policy_name": "default_policy",
        "min_margin_percent": 12.0,        # Demo merchant profit floor
        "max_discount_percent": 15.0,      # Demo merchant discount ceiling
        "allow_bundles": True,
        "allow_substitutions": True,
        "weight_margin": 0.4,
        "weight_revenue": 0.3,
        "weight_overstock": 0.2,
        "weight_discount_penalty": 0.1,
        "is_active": True,
    }
]

def seed_policies(update_existing=True):
    db = SessionLocal()
    try:
        created = 0
        updated = 0
        for policy_data in DEFAULT_POLICIES:
            name = policy_data["policy_name"]
            existing = db.execute(select(MerchantPolicy).where(MerchantPolicy.policy_name == name)).scalar_one_or_none()

            if existing:
                if update_existing:
                    for k, v in policy_data.items():
                        setattr(existing, k, v)
                    updated += 1
            else:
                policy = MerchantPolicy(**policy_data)
                db.add(policy)
                created += 1

        db.commit()
        print(f"Policy seeding completed! ({created} created, {updated} updated)")
    except Exception as e:
        db.rollback()
        print(f"Error seeding policy: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_policies()
