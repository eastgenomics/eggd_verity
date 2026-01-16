import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_SECRET_CACHE: dict[str, Any] | None = None


def load_secrets(secret_name: str, region_name: str = "eu-west-2") -> dict[str, Any]:
    """
    Load secrets from AWS Secrets Manager.

    Parameters
    ----------
    secret_name : str
        The name of the secret to retrieve.
    region_name : str, optional
        The AWS region where the secret is stored, by default "eu-west-2".

    Returns
    -------
    dict[str, Any]
        A dictionary containing the secrets.

    Raises
    ------
    RuntimeError
        If the secret cannot be retrieved or is empty.
    """
    global _SECRET_CACHE

    if _SECRET_CACHE is not None:
        return _SECRET_CACHE

    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager",
        region_name=region_name,
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"Unable to load secrets: {e}")
        raise RuntimeError(f"Unable to load secrets: {e}")

    secret_string = response.get("SecretString")
    if not secret_string:
        logger.error("SecretString is empty")
        raise RuntimeError("SecretString is empty")

    secrets = json.loads(secret_string)
    _SECRET_CACHE = secrets
    return secrets
