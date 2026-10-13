import pytest

from app.services.lazada_cookie_manager import LazadaCookieManager


def test_cookie_profile_validation_accepts_browser_cookie_export():
    LazadaCookieManager.validate_cookies([
        {"name": "_m_h5_tk", "value": "session-value", "domain": ".lazada.vn", "path": "/"},
    ])


@pytest.mark.parametrize("cookies", [[], [{"name": "missing-value"}], [{"name": "", "value": "x"}], "not-a-list"])
def test_cookie_profile_validation_rejects_invalid_or_empty_payloads(cookies):
    with pytest.raises(ValueError):
        LazadaCookieManager.validate_cookies(cookies)
