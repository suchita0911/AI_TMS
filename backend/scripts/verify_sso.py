"""Pre-demo sanity check for the Entra ID (OIDC) SSO configuration.

Verifies that SSO_TENANT_ID / SSO_CLIENT_ID / SSO_CLIENT_SECRET are set and that
the tenant's OpenID discovery document is reachable, then prints the exact
authorization URL the login button will use. No sign-in happens — this only
confirms the config resolves against Microsoft before you demo.

Run from the backend directory:
    python -m scripts.verify_sso
"""
from __future__ import annotations

import sys

import httpx

from app.core.config import settings
from app.core import oidc


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _ok(msg: str) -> None:
    print(f"  [ok]   {msg}")


def main() -> int:
    print("SSO configuration check")
    print("-" * 60)

    # 1. Are the three required values present?
    missing = [
        name
        for name in ("SSO_TENANT_ID", "SSO_CLIENT_ID", "SSO_CLIENT_SECRET")
        if not getattr(settings, name)
    ]
    if missing:
        _fail(f"missing env values: {', '.join(missing)}")
        print("\nSSO is DISABLED until all three are set in backend/.env.")
        return 1
    _ok("SSO_TENANT_ID / SSO_CLIENT_ID / SSO_CLIENT_SECRET are set")
    _ok(f"auto-provision: {settings.SSO_AUTO_PROVISION} "
        f"({'unknown emails auto-created' if settings.SSO_AUTO_PROVISION else 'only pre-created accounts may log in'})")

    # 2. Can we reach the tenant's discovery document?
    authority = f"https://login.microsoftonline.com/{settings.SSO_TENANT_ID}/v2.0"
    disco_url = f"{authority}/.well-known/openid-configuration"
    try:
        resp = httpx.get(disco_url, timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        _fail(f"could not load discovery document: {exc}")
        _fail("check that SSO_TENANT_ID is a valid Directory (tenant) ID/domain")
        return 1
    disco = resp.json()
    _ok(f"discovery document loaded ({disco_url})")
    _ok(f"issuer: {disco.get('issuer')}")

    # 3. Can we reach the signing keys (JWKS)?
    try:
        jwks = httpx.get(disco["jwks_uri"], timeout=10.0)
        jwks.raise_for_status()
    except httpx.HTTPError as exc:
        _fail(f"could not load JWKS signing keys: {exc}")
        return 1
    _ok(f"JWKS signing keys loaded ({len(jwks.json().get('keys', []))} key(s))")

    # 4. Show the redirect URI and the authorization URL the app will build.
    print("-" * 60)
    print(f"Redirect URI (must match the App registration exactly):\n  {settings.SSO_REDIRECT_URI}")
    print(f"\nPost-login page (frontend receives tokens here):\n  {settings.SSO_POST_LOGIN_URL}")
    try:
        auth_url = oidc.authorization_url()
        print(f"\nAuthorization URL the login button will use:\n  {auth_url}")
    except oidc.SSOError as exc:
        _fail(f"could not build authorization URL: {exc}")
        return 1

    print("-" * 60)
    print("All checks passed. SSO is ready. (Client secret validity is only")
    print("proven by a real sign-in — click the SSO button once to confirm.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
