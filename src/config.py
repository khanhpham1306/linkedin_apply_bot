"""Centralised environment variable loading and validation."""

import json
import os


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(f"Required environment variable '{key}' is not set")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class Config:
    def __init__(self) -> None:
        self.google_service_account_json: str = _require("GOOGLE_SERVICE_ACCOUNT_JSON")
        self.google_sheet_id: str = _require("GOOGLE_SHEET_ID")
        self.telegram_bot_token: str = _require("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id: str = _require("TELEGRAM_CHAT_ID")
        self.github_run_id: str = _optional("GITHUB_RUN_ID", "local")
        self.anthropic_api_key: str = _optional("ANTHROPIC_API_KEY")

    def google_service_account_info(self) -> dict:
        """Parse the service account JSON string into a dict."""
        return json.loads(self.google_service_account_json)


def load() -> Config:
    """Load and validate all required configuration from environment variables."""
    return Config()
