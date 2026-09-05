"""Tests for the organization abstraction (ORGANIZATION_PLAN.md): profile
loading/fallback/error behavior, that each profile's seed data actually
seeds, and that authorization logic never depends on team/tag names."""

import re
from importlib import import_module
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.core.config import get_settings
from app.core.organization import get_active_organization
from app.db.base import Base
from app.models.project import Project
from app.models.tag import Tag
from app.models.team import Team
from app.models.user import User


@pytest.fixture(autouse=True)
def _clear_organization_caches():
    """get_settings() and get_active_organization() are both process-wide
    lru_caches — clear them before and after each test in this file so a
    monkeypatched APP_ORGANIZATION never leaks into unrelated tests."""
    get_settings.cache_clear()
    get_active_organization.cache_clear()
    yield
    get_settings.cache_clear()
    get_active_organization.cache_clear()


def _memory_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_default_organization_is_the_fallback_when_unset(monkeypatch):
    monkeypatch.delenv("APP_ORGANIZATION", raising=False)
    org = get_active_organization()
    assert org.id == "default"


def test_known_organization_resolves(monkeypatch):
    monkeypatch.setenv("APP_ORGANIZATION", "vortex")
    org = get_active_organization()
    assert org.id == "vortex"
    assert org.product_name == "Vortex NTNU"


def test_unknown_organization_raises_clear_error(monkeypatch):
    from app.core.organization import UnknownOrganizationError

    monkeypatch.setenv("APP_ORGANIZATION", "does-not-exist")
    with pytest.raises(UnknownOrganizationError, match="does-not-exist"):
        get_active_organization()


@pytest.mark.parametrize("org_id", ["default", "vortex"])
def test_profile_seed_data_seeds_successfully(org_id: str):
    session = _memory_session()
    try:
        seed_module = import_module(f"app.organizations.{org_id}.seed_data")
        seed_module.seed(session)
        session.commit()

        assert session.query(Project).count() == 1
        assert session.query(Team).count() > 0
        assert session.query(Tag).count() > 0
        assert session.query(User).count() > 0
    finally:
        session.close()


def test_default_organization_boots_with_zero_vortex_assets():
    """The neutral profile's actual data — branding and seed content, not
    prose in comments/docstrings — must not reference anything Vortex."""
    from app.organizations.default import config as default_config
    from app.organizations.default import seed_data as default_seed

    vortex_markers = ("Vortex", "AUV", "Mechanical", "Electrical", "Embedded", "Perception")

    assert not any(marker in default_config.ORGANIZATION.name for marker in vortex_markers)
    assert not any(marker in default_config.ORGANIZATION.product_name for marker in vortex_markers)

    team_and_tag_names = [name for name, _category in default_seed.TEAM_DEFS]
    team_and_tag_names += default_seed.TAG_NAMES
    team_and_tag_names += [name for name, _email, _role in default_seed.USER_DEFS]

    session = _memory_session()
    try:
        default_seed.seed(session)
        session.commit()
        project = session.query(Project).one()
        team_and_tag_names += [project.name, project.description]
    finally:
        session.close()

    for marker in vortex_markers:
        assert not any(marker in value for value in team_and_tag_names), (
            f"default profile data must not reference {marker!r}"
        )


def test_permissions_module_never_hardcodes_team_or_tag_names():
    """AUTHORIZATION.md's own rule: authorization resolves teams/tags by ID
    via TeamMembership, never by comparing literal names — otherwise the
    org-abstraction couldn't swap team rosters between deployments safely."""
    import app.core.permissions as permissions_module

    source = Path(permissions_module.__file__).read_text(encoding="utf-8")

    all_team_and_tag_names: set[str] = set()
    for org_id in ("default", "vortex"):
        seed_module = import_module(f"app.organizations.{org_id}.seed_data")
        all_team_and_tag_names.update(name for name, _category in seed_module.TEAM_DEFS)
        all_team_and_tag_names.update(seed_module.TAG_NAMES)

    for name in all_team_and_tag_names:
        assert not re.search(rf'"{re.escape(name)}"', source), (
            f"app/core/permissions.py must not hardcode the team/tag name {name!r} — "
            "authorization must resolve by ID via TeamMembership instead."
        )
