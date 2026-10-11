import asyncio
import pytest
from app.services.providers.lazada import LazadaPriceProvider
from app.services.providers.base import ProductScrapedData
from app.services.providers.factory import get_price_provider_for_url


def test_lazada_provider_html_json_ld_parsing():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Chuột Gaming Logitech G Pro X Superlight Wireless",
            "image": "https://vn-live-01.slatic.net/p/logitech.jpg",
            "offers": {
                "@type": "Offer",
                "price": "1290000",
                "priceCurrency": "VND"
            }
        }
        </script>
    </head>
    <body></body>
    </html>
    """
    provider = LazadaPriceProvider()
    data = provider._parse_html(html, "https://www.lazada.vn/products/logitech-g-pro-i123.html")
    assert data is not None
    assert data.success is True
    assert data.name == "Chuột Gaming Logitech G Pro X Superlight Wireless"
    assert data.price == 1290000
    assert data.image_url == "https://vn-live-01.slatic.net/p/logitech.jpg"


def test_lazada_provider_script_init_data_parsing():
    html = """
    <html>
    <head>
        <title>Sony WH-1000XM5</title>
        <script>
            window.__INIT_DATA__ = {
                "root": {
                    "fields": {
                        "skuInfos": {
                            "0": {
                                "price": {"value": 6490000},
                                "salePrice": {"value": 5990000},
                                "originalPrice": {"value": 8490000}
                            }
                        }
                    }
                }
            };
        </script>
    </head>
    </html>
    """
    provider = LazadaPriceProvider()
    data = provider._parse_html(html, "https://www.lazada.vn/products/sony-wh-1000xm5-i456.html")
    assert data is not None
    assert data.price == 5990000
    assert data.original_price == 8490000


def test_provider_factory():
    provider = get_price_provider_for_url("https://www.lazada.vn/products/test-i123.html")
    assert isinstance(provider, LazadaPriceProvider)


def test_lazada_login_page_is_classified_as_session_expired(monkeypatch):
    provider = LazadaPriceProvider()

    async def login_page(_url):
        return "<html><body><form>login password</form></body></html>"

    async def no_playwright(_url, _sku):
        return None

    monkeypatch.setattr(provider, "_fetch_html", login_page)
    monkeypatch.setattr(provider, "_fetch_with_playwright", no_playwright)

    data = asyncio.run(provider.get_product_info("https://www.lazada.vn/products/test-i123.html", use_cache=False))

    assert data.success is False
    assert data.error_code == "SESSION_EXPIRED"


def test_lazada_prefers_session_aware_dynamic_price_over_static_html(monkeypatch):
    """The signed-in PDP price must win when static HTML exposes a base price."""
    provider = LazadaPriceProvider()
    product_url = "https://www.lazada.vn/products/test-product-i123.html"

    async def static_product_page(_url):
        return "<html><head><title>Test product</title></head><body>product</body></html>"

    static_data = ProductScrapedData(
        name="Test product",
        price=1_567_000,
        original_price=1_900_000,
        url=product_url,
    )
    dynamic_data = ProductScrapedData(
        name="Test product",
        price=820_350,
        original_price=1_567_000,
        url=product_url,
    )

    monkeypatch.setattr(provider, "_fetch_html", static_product_page)
    monkeypatch.setattr(provider, "_parse_html", lambda _html, _url: static_data)
    monkeypatch.setattr(provider, "_has_saved_browser_session", lambda: True)

    async def dynamic_product_page(_url, _sku):
        return dynamic_data

    monkeypatch.setattr(provider, "_fetch_with_playwright", dynamic_product_page)

    data = asyncio.run(provider.get_product_info(product_url, use_cache=False))

    assert data.success is True
    assert data.price == 820_350
    assert data.original_price == 1_567_000
