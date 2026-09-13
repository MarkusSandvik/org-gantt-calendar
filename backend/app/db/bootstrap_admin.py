"""Create the first real Admin account on a fresh database, with no demo
data. Run with: python -m app.db.bootstrap_admin --email you@example.org --name "Your Name"

This is the answer to the gap described in DEPLOYMENT_PLAN.md's
"Bootstrapping a real production database" section: `app/db/seed.py` only
knows how to load an organization's fake demo data (teams, activities, and
shared-password demo users), so a real deployment has no way to get just
one real Admin. This script solves exactly that first chicken-and-egg
problem — every other structure (Teams, Tags, the first real Project, more
Users) is already reachable through the Admin UI once one Admin exists.

Refuses to run against a database that already has any User, so it can
never turn into a second, conflicting way to seed data alongside
app/db/seed.py.
"""

import argparse
import secrets

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User


def bootstrap_admin(email: str, name: str, password: str | None = None) -> str:
    """Create exactly one Admin user. Returns the password used (either the
    one supplied, or a freshly generated one the caller must record — it is
    never logged or stored anywhere else)."""
    db = SessionLocal()
    try:
        if db.query(User).first() is not None:
            raise RuntimeError(
                "Refusing to bootstrap: the users table is not empty. This "
                "script only ever creates the first Admin on an otherwise "
                "empty database — use the Admin UI's invitation flow to add "
                "more accounts."
            )

        generated = password is None
        if generated:
            password = secrets.token_urlsafe(18)

        admin = User(
            name=name,
            email=email,
            global_role=GlobalRole.ADMIN,
            status=UserStatus.ACTIVE,
            password_hash=hash_password(password),
        )
        db.add(admin)
        db.commit()
        return password
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Real email address for the Admin account")
    parser.add_argument("--name", required=True, help="Display name for the Admin account")
    parser.add_argument(
        "--password",
        default=None,
        help="Password to set (omit to generate a random one, printed once below)",
    )
    args = parser.parse_args()

    password = bootstrap_admin(args.email, args.name, args.password)

    print(f"Admin created: {args.email}")
    if args.password is None:
        print(f"Generated password (shown once, not stored anywhere else): {password}")
        print("Log in and treat this as a one-time credential — there is no forced")
        print("password-change flow yet, so share and rotate it out-of-band if needed.")


if __name__ == "__main__":
    main()
