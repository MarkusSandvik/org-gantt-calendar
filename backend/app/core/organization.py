"""Deployment-level organization identity. Not a database concept — see
ORGANIZATION_PLAN.md's "Decisions" section for why. Exactly one profile is
active per running process, selected once at startup by APP_ORGANIZATION
(defaults to "default" so local dev needs no configuration).

A profile is a plain Python module at app/organizations/<id>/config.py.
It exports an ORGANIZATION constant (this dataclass) plus the seed-time
data consumed by app/db/seed.py — see that module for the full contract.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module

from app.core.config import get_settings


@dataclass(frozen=True)
class OrganizationConfig:
    id: str
    name: str
    short_name: str
    product_name: str
    # Typed, deliberately flat feature flags — see app/extensions/README.md.
    # Not a database table: a flag change is a redeploy, matching the
    # single-org-per-deployment model this app targets.
    features: dict[str, bool] = field(default_factory=dict)


class UnknownOrganizationError(RuntimeError):
    pass


@lru_cache
def get_active_organization() -> OrganizationConfig:
    org_id = get_settings().organization
    try:
        module = import_module(f"app.organizations.{org_id}.config")
    except ModuleNotFoundError as exc:
        raise UnknownOrganizationError(
            f"Unknown APP_ORGANIZATION={org_id!r} — no app/organizations/{org_id}/"
            f"config.py profile exists. Set APP_ORGANIZATION to an existing "
            f"profile id, or add a new one (see ORGANIZATION_PLAN.md)."
        ) from exc
    return module.ORGANIZATION
