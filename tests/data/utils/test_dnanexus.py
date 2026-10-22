import logging
import os
from unittest.mock import patch

os.environ.setdefault("DX_TOKEN", "test-token")

from data.utils import dnanexus  # noqa: E402

TOKEN = "super-secret-dx-token"


def test_login_does_not_leak_token(capsys, caplog):
    caplog.set_level(logging.DEBUG)
    with patch.object(dnanexus.dxpy, "set_security_context") as set_ctx, patch.object(
        dnanexus.dxpy, "whoami"
    ):
        dnanexus.login_to_dnanexus(TOKEN)

    set_ctx.assert_called_once_with({"auth_token_type": "Bearer", "auth_token": TOKEN})
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    assert TOKEN not in caplog.text
