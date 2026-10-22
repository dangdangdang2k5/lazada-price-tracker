import asyncio
import json
import pytest

from app.core.config import settings
from app.services.providers.base import ProductScrapedData
from app.services.providers.factory import get_price_provider_for_url
from app.services.providers.lazada import LazadaPriceProvider
from app.services.providers.lazada_api import LazadaApiProvider
from app.services.providers.lazada_authenticated import AuthenticatedLazadaPriceProvider
from app.services.providers.lazada_pdp_client import LazadaPdpClient


def test_extract_item_and_sku_id():
    """Verify regex extraction of itemId and skuId from diverse URL formats."""
    # Standard desktop URL with SKU
    url1 = "https://www.lazada.vn/products/ban-phim-co-f75-i3300646509-s16055633476.html?spm=a2o4n.searchlist"
    item1, sku1 = LazadaApiProvider.extract_item_and_sku_id(url1)
    assert item1 == "3300646509"
    assert sku1 == "16055633476"

    # URL without SKU
    url2 = "https://www.lazada.vn/products/chuot-logitech-i12345678.html"
    item2, sku2 = LazadaApiProvider.extract_item_and_sku_id(url2)
    assert item2 == "12345678"
    assert sku2 is None

    # URL with query parameters
    url3 = "https://www.lazada.vn/products/?itemId=998877&skuId=445566"
    item3, sku3 = LazadaApiProvider.extract_item_and_sku_id(url3)
    assert item3 == "998877"
    assert sku3 == "445566"

    # Empty or invalid URL
    item4, sku4 = LazadaApiProvider.extract_item_and_sku_id("")
    assert item4 is None
    assert sku4 is None

    # Slugless and double-slash URL
    url5 = "https://www.lazada.vn//products/i3276673627-s15829337083.html"
    item5, sku5 = LazadaApiProvider.extract_item_and_sku_id(url5)
    assert item5 == "3276673627"
    assert sku5 == "15829337083"

    pdp_item, pdp_sku = LazadaPdpClient.extract_item_and_sku_id(url5)
    assert pdp_item == "3276673627"
    assert pdp_sku == "15829337083" 


def test_parse_mtop_response():
    """Verify parsing logic on mocked MTOP response JSON."""
    provider = LazadaApiProvider()
    url = "https://www.lazada.vn/products/sample-i100-s200.html"

    mock_mod = {
        "product": {"title": "Tai nghe không dây Bluetooth Pro Max"},
        "productOption": {
            "skuBase": {
                "properties": [
                    {
                        "pid": "1001",
                        "name": "Màu sắc",
                        "values": [
                            {"vid": "1", "name": "Đen Matte"},
                            {"vid": "2", "name": "Trắng Bạc"},
                        ],
                    }
                ],
                "skus": [
                    {"skuId": "200", "propPath": "1001:1", "pagePath": "/products/sample-i100-s200.html"},
                    {"skuId": "201", "propPath": "1001:2", "pagePath": "/products/sample-i100-s201.html"},
                ],
            }
        },
        "skuInfos": {
            "200": {
                "price": {
                    "salePrice": {"value": 750000},
                    "originalPrice": {"value": 1200000},
                    "coupon": {"priceNumber": 699000},
                },
                "quantity": {"text": "Còn hàng", "limit": {"max": 10}},
                "image": "https://img.lazcdn.com/black.jpg",
            },
            "201": {
                "price": {
                    "salePrice": {"value": 850000},
                    "originalPrice": {"value": 1200000},
                },
                "quantity": {"text": "Hết hàng", "limit": {"max": 0}},
                "image": "https://img.lazcdn.com/white.jpg",
            },
        },
    }

    mock_response = {
        "ret": ["SUCCESS::调用成功"],
        "data": {"module": json.dumps(mock_mod)},
    }

    data = provider._parse_mtop_response(mock_response, url, "100", "200")

    assert data is not None
    assert data.success is True
    assert data.name == "Tai nghe không dây Bluetooth Pro Max"
    # Coupon price takes precedence
    assert data.price == 699000
    assert data.original_price == 1200000
    assert data.sku_id == "200"
    assert data.sku_name == "Đen Matte"
    assert data.image_url == "https://img.lazcdn.com/black.jpg"
    assert len(data.variations) == 2

    # Check variation availability
    assert data.variations[0]["available"] is True
    assert data.variations[1]["available"] is False


def test_factory_routing():
    """Verify get_price_provider_for_url respects PRICE_PROVIDER_MODE configuration."""
    url = "https://www.lazada.vn/products/sample-i100.html"

    # Explicit mode 'api'
    p_api = get_price_provider_for_url(url, mode="api")
    assert isinstance(p_api, (AuthenticatedLazadaPriceProvider, LazadaApiProvider))

    # Explicit mode 'scraper'
    p_scraper = get_price_provider_for_url(url, mode="scraper")
    assert isinstance(p_scraper, LazadaPriceProvider)

    # Default mode adheres to settings
    default_p = get_price_provider_for_url(url)
    if settings.PRICE_PROVIDER_MODE == "api":
        assert isinstance(default_p, (AuthenticatedLazadaPriceProvider, LazadaApiProvider))
    else:
        assert isinstance(default_p, LazadaPriceProvider)


@pytest.mark.asyncio
async def test_live_mtop_api_fetch():
    """
    Live probe test against Lazada mobile gateway with a real sample product URL.
    Verifies that no browser is launched, status is 200 SUCCESS, and full SKU variations are returned.
    """
    provider = LazadaApiProvider()
    real_url = (
        "https://www.lazada.vn/products/"
        "aula-ban-phim-co-f75-khong-day-3-che-do-gasket-mount-hotswap-layout-75-co-num-xoay"
        "-i3300646509-s16055633476.html"
    )

    result = await provider.get_product_info(real_url, use_cache=False)

    assert result is not None
    assert result.success is True
    assert result.price > 0
    assert result.sku_id == "16055633476"
    assert "AULA" in result.name or "Bàn Phím" in result.name or "F75" in result.name
    assert len(result.variations) > 0
    assert result.image_url is not None and result.image_url.startswith("http")


@pytest.mark.asyncio
async def test_live_slugless_and_double_slash_url_fetch():
    """
    Verify that AuthenticatedLazadaPriceProvider and LazadaPdpClient handle slugless URLs
    with consecutive slashes, e.g. https://www.lazada.vn//products/i3276673627-s15829337083.html.
    """
    provider = AuthenticatedLazadaPriceProvider()
    url = "https://www.lazada.vn//products/i3276673627-s15829337083.html"

    result = await provider.get_product_info(url, use_cache=False)

    assert result is not None
    assert result.success is True
    assert result.sku_id == "15829337083"
    assert result.price > 0
    assert "AULA" in result.name or "WiN60" in result.name
    assert len(result.variations) > 0


def test_cookie_persistence_updates_file(tmp_path, monkeypatch):
    """Verify _persist_session_cookies saves and updates cookies in JSON file."""
    test_cookie_file = tmp_path / "lazada_cookies.json"
    monkeypatch.setattr(settings, "LAZADA_COOKIE_FILE", str(test_cookie_file))

    # Initial write
    LazadaPdpClient._persist_session_cookies({"_m_h5_tk": "initial_token_123", "user_sess": "abc"})
    assert test_cookie_file.is_file()

    data = json.loads(test_cookie_file.read_text(encoding="utf-8"))
    cookie_map = {c["name"]: c["value"] for c in data}
    assert cookie_map["_m_h5_tk"] == "initial_token_123"
    assert cookie_map["user_sess"] == "abc"

    # Incremental update
    LazadaPdpClient._persist_session_cookies({"_m_h5_tk": "refreshed_token_456", "new_pref": "dark"})
    data2 = json.loads(test_cookie_file.read_text(encoding="utf-8"))
    cookie_map2 = {c["name"]: c["value"] for c in data2}
    assert cookie_map2["_m_h5_tk"] == "refreshed_token_456"
    assert cookie_map2["user_sess"] == "abc"
    assert cookie_map2["new_pref"] == "dark"


@pytest.mark.asyncio
async def test_pdp_client_retries_on_token_expired(monkeypatch):
    """
    Verify that LazadaPdpClient catches FAIL_SYS_TOKEN_EXOIRED,
    reads new token from cookies, and immediately retries to return valid data.
    """
    client = LazadaPdpClient()
    mock_mod = {
        "product": {"title": "Test Retry Product"},
        "productOption": {"skuBase": {"properties": [], "skus": [{"skuId": "999", "propPath": ""}]}},
        "skuInfos": {"999": {"price": {"salePrice": {"value": 500000}}}},
    }
    call_count = 0

    class MockResponse:
        def __init__(self, json_data, cookies=None, text=""):
            self.status_code = 200
            self._json = json_data
            self.cookies = cookies or {}
            self.text = text or json.dumps(json_data)

        def json(self):
            return self._json

    async def mock_get(self_client, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if "getdetailinfo" in str(url) or "mtop" in str(url):
            if call_count == 1:
                # Return expired token error with refreshed cookie in response
                return MockResponse(
                    {"ret": ["FAIL_SYS_TOKEN_EXOIRED::令牌过期"], "data": {}},
                    cookies={"_m_h5_tk": "newtoken123_1799999999999"}
                )
            else:
                # Return success on immediate retry
                return MockResponse({
                    "ret": ["SUCCESS::调用成功"],
                    "data": {"module": json.dumps(mock_mod)}
                })
        return MockResponse({"ret": ["SUCCESS"]}, text="<html><body>PDP</body></html>")

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    result = await client.fetch_pdp_snapshot("https://www.lazada.vn/products/item-i123-s999.html")
    assert call_count >= 2
    assert result.success is True
    assert result.chosen_variation is not None
    assert result.chosen_variation.price == 500000
    assert result.chosen_variation.sku_id == "999"


@pytest.mark.asyncio
async def test_product_service_refresh_with_authenticated_provider(monkeypatch):
    """
    Verify ProductService.refresh_product_price saves updated price to DB
    and triggers target price alert smoothly with AuthenticatedLazadaPriceProvider.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.core.database import Base
    from app.models.product import Product
    from app.models.alert import Alert, AlertType
    from app.services.product_service import ProductService
    from app.services.lazada_cookie_manager import cookie_manager, CookieFetchOutcome

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    TestSession = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mock provider result
    fake_scraped = ProductScrapedData(
        name="AULA Keyboard Pro Updated",
        price=1800000,
        original_price=2500000,
        sku_id="16055633476",
        sku_name="Reaper Axis",
        url="https://www.lazada.vn/products/keyboard-i100-s16055633476.html",
        variations=[{"sku_id": "16055633476", "name": "Reaper Axis", "price": 1800000, "available": True}],
        success=True,
    )

    async def mock_fetch_product(url, use_cache=True):
        return CookieFetchOutcome(data=fake_scraped, active_profile_id=None)

    monkeypatch.setattr(cookie_manager, "fetch_product", mock_fetch_product)

    async with TestSession() as session:
        p = Product(
            name="AULA Keyboard Old",
            url="https://www.lazada.vn/products/keyboard-i100-s16055633476.html",
            sku_id="16055633476",
            current_price=2200000,
            lowest_price=2200000,
            highest_price=2200000,
            active=True
        )
        session.add(p)
        await session.flush()
        alert = Alert(
            product_id=p.id,
            alert_type=AlertType.TARGET_PRICE.value,
            target_price=2000000,
            enabled=True,
            is_triggered=False
        )
        session.add(alert)
        await session.commit()
        prod_id = p.id

    async with TestSession() as session:
        service = ProductService(session)
        updated = await service.refresh_product_price(prod_id)
        assert updated is not None
        assert updated.current_price == 1800000
        assert updated.is_target_reached is True

        alerts = await service.alert_repo.get_by_product(prod_id)
        target_alert = next(a for a in alerts if a.alert_type == AlertType.TARGET_PRICE.value)
        assert target_alert.is_triggered is True
