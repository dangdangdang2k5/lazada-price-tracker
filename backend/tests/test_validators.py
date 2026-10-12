import pytest
from app.utils.validators import is_valid_lazada_url, normalize_lazada_url


def test_valid_lazada_urls():
    valid_urls = [
        "https://www.lazada.vn/products/chuot-gaming-logitech-g-pro-x-i12345678-s87654321.html",
        "https://lazada.vn/products/tai-nghe-sony-wh1000xm5-i999999.html?spm=a2o4n.search",
        "https://s.lazada.vn/s.abcd",
        "https://www.lazada.co.th/products/test-i123.html",
    ]
    for url in valid_urls:
        assert is_valid_lazada_url(url) is True


def test_invalid_urls():
    invalid_urls = [
        "https://www.shopee.vn/product/123/456",
        "https://google.com",
        "invalid-url-string",
        "",
        None,
    ]
    for url in invalid_urls:
        assert is_valid_lazada_url(url) is False


def test_normalize_lazada_url():
    url_with_tracking = "https://www.lazada.vn/products/logitech-g-pro-i123.html?spm=a2o4n.home&clickTrackInfo=abc123xyz"
    normalized = normalize_lazada_url(url_with_tracking)
    assert normalized == "https://www.lazada.vn/products/logitech-g-pro-i123.html"


def test_normalize_lazada_url_removes_expiring_share_tokens_but_keeps_sku_path():
    shared_url = (
        "https://www.lazada.vn/products/aula-f75-i3300646509-s16055633476.html"
        "?tradePath=omItm&laz_token=expired-token&exlaz=signature&sub_id2=123#reviews"
    )

    normalized = normalize_lazada_url(shared_url)

    assert normalized == "https://www.lazada.vn/products/aula-f75-i3300646509-s16055633476.html"
