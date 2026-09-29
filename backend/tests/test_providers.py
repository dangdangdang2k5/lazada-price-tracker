import pytest
from app.services.providers.lazada import LazadaPriceProvider
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
