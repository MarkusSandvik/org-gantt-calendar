import datetime as dt
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def utc_now() -> dt.datetime:
    """A naive UTC timestamp. SQLite has no real datetime type — it stores
    values as ISO strings and always returns naive datetimes on read back,
    so anything compared against a freshly-read column (expiry checks,
    mainly) must be naive too, or the comparison raises TypeError."""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_token() -> str:
    """A cryptographically random, URL-safe token for sessions, invitations,
    and password resets. 32 bytes (256 bits) resists brute-force guessing
    far beyond what any expiry window needs to defend against."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only this hash is ever persisted for a session/invitation/reset
    token — a database leak alone can't be replayed as a live credential."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
