from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import parse_bool
from app.main import configure_auth


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
def test_parse_bool_enabled_values(value):
    assert parse_bool(value, "TEST_SETTING") is True


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off"])
def test_parse_bool_disabled_values(value):
    assert parse_bool(value, "TEST_SETTING") is False


def test_parse_bool_rejects_ambiguous_values():
    with pytest.raises(ValueError, match="TEST_SETTING"):
        parse_bool("maybe", "TEST_SETTING")


def test_configure_auth_does_not_attach_auth_when_disabled():
    app = object()
    settings = SimpleNamespace(
        AUTH_ENABLED=False,
        USERNAME="",
        PASSWORD="",
    )

    with patch("app.main.dash_auth.BasicAuth") as basic_auth:
        assert configure_auth(app, settings) is None
        basic_auth.assert_not_called()


def test_configure_auth_attaches_auth_with_credentials_when_enabled():
    app = object()
    settings = SimpleNamespace(
        AUTH_ENABLED=True,
        USERNAME="test-user",
        PASSWORD="test-password",
    )

    with patch("app.main.dash_auth.BasicAuth") as basic_auth:
        configure_auth(app, settings)
        basic_auth.assert_called_once_with(app, {"test-user": "test-password"})
