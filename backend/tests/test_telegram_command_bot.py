import json

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
