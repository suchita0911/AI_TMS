"""Idempotent database bootstrap: create tables, seed roles and first admin."""
from __future__ import annotations

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging_config import get_logger
from app.core.security import hash_password
from app.models.enums import RoleName, UserStatus
from app.models.user import Role, User
from app.repositories.user_repository import RoleRepository, UserRepository

logger = get_logger(__name__)

_ROLE_DESCRIPTIONS = {
    RoleName.ADMIN: "Full administrative access",
    RoleName.EMPLOYEE: "Standard learner access",
}


def create_tables() -> None:
    # Import models package so every table is registered on the metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")


def seed_roles(db) -> None:
    repo = RoleRepository(db)
    for role_name, desc in _ROLE_DESCRIPTIONS.items():
        if not repo.get_by_name(role_name):
            db.add(Role(name=role_name, description=desc))
            logger.info("Seeded role: %s", role_name.value)
    db.commit()


def seed_admin(db) -> None:
    users = UserRepository(db)
    # Idempotent: skip if the bootstrap admin already exists by username OR email
    # (the username may have been changed after first setup).
    if users.get_by_username(settings.FIRST_ADMIN_USERNAME) or users.get_by_email(settings.FIRST_ADMIN_EMAIL):
        return
    admin_role = RoleRepository(db).get_by_name(RoleName.ADMIN)
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
    db.commit()
    logger.info("Seeded first admin user: %s", settings.FIRST_ADMIN_USERNAME)


def init_db() -> None:
    create_tables()
    with SessionLocal() as db:
        seed_roles(db)
        seed_admin(db)
