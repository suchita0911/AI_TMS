"""Pytest fixtures: isolated test database + FastAPI TestClient.

Uses a dedicated ``tms_test`` PostgreSQL database that is dropped and recreated
for each test session so tests never touch development data.
"""
from __future__ import annotations

import os

# Point the app at the test database BEFORE any app import.
os.environ["POSTGRES_DB"] = "tms_test"
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"

import psycopg2  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402


def _recreate_test_db() -> None:
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname="postgres",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS tms_test WITH (FORCE)")
        cur.execute("CREATE DATABASE tms_test")
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    _recreate_test_db()
    from app.core.bootstrap import init_db

    init_db()
    yield


@pytest.fixture(scope="session")
def client(_db_setup) -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token(client) -> str:
    resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"username": settings.FIRST_ADMIN_USERNAME, "password": settings.FIRST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
