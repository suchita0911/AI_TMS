"""Idempotent database bootstrap: create tables, seed roles and first admin."""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging_config import get_logger
from app.core.security import hash_password
from app.models.enums import RoleName, UserStatus
from app.models.user import Designation, Role, User
from app.repositories.user_repository import (
    DesignationRepository,
    RoleRepository,
    UserRepository,
)

logger = get_logger(__name__)

_ROLE_DESCRIPTIONS = {
    RoleName.ADMIN: "Full administrative access",
    RoleName.EMPLOYEE: "Standard learner access",
}

# Curated starter list of job designations. Admins can add more at runtime; this
# just guarantees a useful set exists out of the box. Keep in sync with the
# frontend DESIGNATIONS fallback in src/types/index.ts.
_DEFAULT_DESIGNATIONS = [
    "Software Engineer",
    "Senior Software Engineer",
    "Tech Lead",
    "Engineering Manager",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "QA Engineer",
    "Automation Test Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "UI/UX Designer",
    "Business Analyst",
    "Product Manager",
    "Project Manager",
    "Scrum Master",
    "Database Administrator",
    "System Administrator",
    "Security Engineer",
    "Support Engineer",
    "Intern / Trainee",
]


def create_tables() -> None:
    # Import models package so every table is registered on the metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    logger.info("Database tables ensured")


# Columns added after the initial schema. ``create_all`` never ALTERs an existing
# table, so for already-provisioned databases we add missing columns here. Kept
# tiny and idempotent (checked against the live schema) as a lightweight stand-in
# for a full migration tool.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "users": {"designation": "VARCHAR(120)"},
}


def _ensure_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
                    logger.info("Added column %s.%s", table, name)


def seed_roles(db) -> None:
    repo = RoleRepository(db)
    for role_name, desc in _ROLE_DESCRIPTIONS.items():
        if not repo.get_by_name(role_name):
            db.add(Role(name=role_name, description=desc))
            logger.info("Seeded role: %s", role_name.value)
    db.commit()


def seed_designations(db) -> None:
    repo = DesignationRepository(db)
    for name in _DEFAULT_DESIGNATIONS:
        if not repo.get_by_name(name):
            db.add(Designation(name=name, is_active=True))
    db.commit()


def seed_admin(db) -> None:
    users = UserRepository(db)
    admin_role = RoleRepository(db).get_by_name(RoleName.ADMIN)
    if not admin_role:
        raise RuntimeError("Admin role is not configured")

    admin = users.get_by_username(settings.FIRST_ADMIN_USERNAME)
    if not admin:
        admin = users.get_by_email(settings.FIRST_ADMIN_EMAIL)

    if admin is None:
        admin = User(
            first_name="System",
            last_name="Administrator",
            username=settings.FIRST_ADMIN_USERNAME,
            email=settings.FIRST_ADMIN_EMAIL,
            role_id=admin_role.id,
            hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
            status=UserStatus.ACTIVE,
            is_active=True,
        )
        db.add(admin)
        logger.info("Seeded first admin user: %s", settings.FIRST_ADMIN_USERNAME)
    else:
        admin.username = settings.FIRST_ADMIN_USERNAME
        admin.email = settings.FIRST_ADMIN_EMAIL
        admin.role_id = admin_role.id
        admin.hashed_password = hash_password(settings.FIRST_ADMIN_PASSWORD)
        admin.status = UserStatus.ACTIVE
        admin.is_active = True
        logger.info("Updated existing admin user credentials")

    db.commit()


def init_db() -> None:
    create_tables()
    with SessionLocal() as db:
        seed_roles(db)
        seed_designations(db)
        seed_admin(db)
