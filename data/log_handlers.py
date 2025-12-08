"""
Custom logging handlers for the Verity data pipeline.
"""

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class SlackWebhookHandler(logging.Handler):
    """
    A logging handler that sends log records to a Slack channel.
    """

    def __init__(self, webhook_url: str):
        """
        Initialises the handler with a Slack Webhook URL.

        Args:
            webhook_url: The Slack Incoming Webhook URL.
        """
        super().__init__()
        self.webhook_url = webhook_url

        # Set up a session with retries for network resilience
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def emit(self, record: logging.LogRecord) -> None:
        """
        Formats the log record and sends it to Slack.
        """
        try:
            log_message = self.format(record)
            # Format the message payload for Slack's webhook API
            payload = {
                "text": f"[{record.levelname}] {record.name}",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f":warning: {record.levelname} in {record.name}"},
                    },
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"```\n{log_message}\n```"}},
                ],
            }
            self.session.post(self.webhook_url, json=payload, timeout=10)
        except Exception:
            self.handleError(record)
