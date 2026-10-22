import pytest
from app.utils.validators import extract_item_and_sku_id, is_valid_lazada_url, normalize_lazada_url


def test_valid_lazada_urls():
    valid_urls = [
        "https://www.lazada.vn/products/chuot-gaming-logitech-g-pro-x-i12345678-s87654321.html",
        "https://www.lazada.vn//products/i3276673627-s15829337083.html",
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


def test_normalize_lazada_url_double_slash_and_slugless():
    raw_url = "https://www.lazada.vn//products/i3276673627-s15829337083.html?exlaz=xyz123"
    normalized = normalize_lazada_url(raw_url)
    assert normalized == "https://www.lazada.vn/products/i3276673627-s15829337083.html"


def test_extract_item_and_sku_id():
    # 1. Double slash and slugless
    item_id, sku_id = extract_item_and_sku_id("https://www.lazada.vn//products/i3276673627-s15829337083.html")
    assert item_id == "3276673627"
    assert sku_id == "15829337083"

    # 2. Slugless without sku
    item_id, sku_id = extract_item_and_sku_id("https://www.lazada.vn/products/i3276673627.html")
    assert item_id == "3276673627"
    assert sku_id is None

    # 3. Standard slug
    item_id, sku_id = extract_item_and_sku_id("https://www.lazada.vn/products/ban-phim-co-aula-i3276673627-s15829337083.html")
    assert item_id == "3276673627"
    assert sku_id == "15829337083"

    # 4. Query params
    item_id, sku_id = extract_item_and_sku_id("https://www.lazada.vn/products/?itemId=3276673627&skuId=15829337083")
    assert item_id == "3276673627"
    assert sku_id == "15829337083"
