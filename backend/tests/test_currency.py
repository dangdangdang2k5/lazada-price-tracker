import pytest
from app.utils.currency import format_currency, parse_currency


def test_format_currency_standard():
    assert format_currency(1290000) == "1.290.000đ"
    assert format_currency(0) == "0đ"
    assert format_currency(500) == "500đ"
    assert format_currency(100000000) == "100.000.000đ"


def test_format_currency_none():
    assert format_currency(None) == "N/A"


def test_parse_currency():
    assert parse_currency("1.290.000 ₫") == 1290000
    assert parse_currency("1,290,000 VND") == 1290000
    assert parse_currency("99.000đ") == 99000
    assert parse_currency("1290000") == 1290000
    assert parse_currency(None) is None
    assert parse_currency("") is None
    assert parse_currency("abc") is None
