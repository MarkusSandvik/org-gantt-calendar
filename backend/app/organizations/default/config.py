"""Neutral, generic organization profile. Ships in the repo so it can run
standalone with zero Vortex-specific assets referenced — see
ORGANIZATION_PLAN.md phase 6.
"""

from app.core.organization import OrganizationConfig

ORGANIZATION = OrganizationConfig(
    id="default",
    name="Example Organization",
    short_name="Example Org",
    product_name="Org Planner",
    features={},
)
