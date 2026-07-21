import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user


def test_missing_bearer_token_returns_a_clear_401() -> None:
    with pytest.raises(HTTPException) as error:
        get_current_user(None)

    assert error.value.status_code == 401
    assert error.value.detail == "Authentication is required. Please sign in again."
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}
