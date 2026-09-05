"""Idempotent demo data seed. Run with: python -m app.db.seed

Which data gets seeded is decided by the active organization profile
(APP_ORGANIZATION, see app/core/organization.py) — this module only
provides the generic skip-if-present / commit / password-hint wrapper
around app/organizations/<id>/seed_data.py's seed(db) function.
"""

from importlib import import_module

from app.core.config import get_settings
from app.core.organization import get_active_organization
from app.db.session import SessionLocal
from app.models.project import Project


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Project).first() is not None:
            print("Seed skipped: data already present.")
            return

        org = get_active_organization()
        seed_module = import_module(f"app.organizations.{org.id}.seed_data")
        seed_module.seed(db)

        db.commit()
        print("Seed complete.")
        print(
            f"All seeded accounts share the development-only password: "
            f"{get_settings().dev_seed_password!r} (see APP_DEV_SEED_PASSWORD)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
