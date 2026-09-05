"""Vortex NTNU organization profile — the original deployment this app was
built for. Seed data (teams/tags/demo project) moves here in phase 2.
"""

from app.core.organization import OrganizationConfig

ORGANIZATION = OrganizationConfig(
    id="vortex",
    name="Vortex NTNU",
    short_name="Vortex",
    product_name="Vortex NTNU",
    features={},
)
