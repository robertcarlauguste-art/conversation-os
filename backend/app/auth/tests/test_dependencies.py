from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_principal
from app.core.config import Settings


def test_development_identity_when_auth_is_disabled() -> None:
    principal = require_principal(
        SimpleNamespace(headers={}),
        Settings(auth_enabled=False, auth_dev_user_id="local_agent"),
    )

    assert principal.user_id == "local_agent"
    assert principal.is_development_identity is True


def test_auth_enabled_requires_clerk_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    state = SimpleNamespace(is_authenticated=False, payload=None)
    monkeypatch.setattr(
        "app.auth.dependencies.Clerk.authenticate_request",
        lambda *_args, **_kwargs: state,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_principal(
            SimpleNamespace(headers={}),
            Settings(auth_enabled=True, clerk_secret_key="sk_test_example"),
        )

    assert exc_info.value.status_code == 401


def test_verified_clerk_subject_becomes_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    state = SimpleNamespace(
        is_authenticated=True,
        payload={"sub": "user_123", "org_id": "org_456"},
    )
    monkeypatch.setattr(
        "app.auth.dependencies.Clerk.authenticate_request",
        lambda *_args, **_kwargs: state,
    )

    principal = require_principal(
        SimpleNamespace(headers={}),
        Settings(auth_enabled=True, clerk_secret_key="sk_test_example"),
    )

    assert principal.user_id == "user_123"
    assert principal.organization_id == "org_456"
    assert principal.is_development_identity is False
