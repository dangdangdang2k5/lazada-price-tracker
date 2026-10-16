import json
from unittest.mock import AsyncMock

import pytest

from app.services.telegram_command_bot import TelegramCommandBot


def test_cookie_upload_accepts_browser_export_list_and_wrapper():
    cookies = [{"name": "_m_h5_tk", "value": "secret", "domain": ".lazada.vn", "path": "/"}]

    assert TelegramCommandBot._validate_cookie_payload(json.dumps(cookies).encode()) == cookies
    assert TelegramCommandBot._validate_cookie_payload(json.dumps({"cookies": cookies}).encode()) == cookies


@pytest.mark.parametrize(
    "payload",
    [b"not-json", b"[]", b'[{"name":"missing-value"}]', b'[{"name":"","value":"x"}]'],
)
def test_cookie_upload_rejects_invalid_payloads(payload):
    with pytest.raises((ValueError, json.JSONDecodeError)):
        TelegramCommandBot._validate_cookie_payload(payload)


def test_cookie_expiration_ignores_invalid_metadata():
    cookies = [
        {"name": "valid", "value": "x", "expirationDate": 1},
        {"name": "bad-date", "value": "x", "expirationDate": "unknown"},
    ]

    assert TelegramCommandBot._expired_cookie_count(cookies) == 1


@pytest.mark.asyncio
async def test_ip_command_sends_resolved_public_address(monkeypatch):
    bot = TelegramCommandBot()
    monkeypatch.setattr(bot, "_resolve_public_ip", AsyncMock(return_value="203.0.113.42"))
    send_message = AsyncMock(return_value=True)
    monkeypatch.setattr("app.services.telegram_command_bot.telegram_service.send_message", send_message)

    await bot._send_public_ip()

    assert "203.0.113.42" in send_message.call_args.args[0]


@pytest.mark.asyncio
async def test_ip_command_reports_lookup_failure(monkeypatch):
    bot = TelegramCommandBot()
    monkeypatch.setattr(bot, "_resolve_public_ip", AsyncMock(return_value=None))
    send_message = AsyncMock(return_value=True)
    monkeypatch.setattr("app.services.telegram_command_bot.telegram_service.send_message", send_message)

    await bot._send_public_ip()

    assert "Không lấy được IP" in send_message.call_args.args[0]
