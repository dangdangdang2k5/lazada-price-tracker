import pytest
from app.models.product import Product
from app.models.alert import Alert, AlertType
from app.services.alert_engine import AlertEngine


@pytest.fixture
def sample_product():
    return Product(
        id=1,
        name="Logitech G Pro X Superlight",
        url="https://www.lazada.vn/products/logitech-g-pro-i123.html",
        current_price=1290000,
        lowest_price=1200000,
        highest_price=1590000,
    )


def test_target_price_alert_triggered(sample_product):
    alert = Alert(
        id=1,
        product_id=1,
        alert_type="TARGET_PRICE",
        target_price=1000000,
        enabled=True,
        is_triggered=False,
    )
    # Price dropped to 950.000 <= 1.000.000
    res = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1200000,
        new_price=950000,
        old_lowest_price=1200000,
        alerts=[alert]
    )
    assert res.should_notify is True
    assert alert.is_triggered is True
    assert alert.last_triggered_price == 950000
    assert any("Đạt giá mục tiêu" in r for r in res.reasons)


def test_target_price_not_reached(sample_product):
    alert = Alert(
        id=1,
        product_id=1,
        alert_type="TARGET_PRICE",
        target_price=1000000,
        enabled=True,
        is_triggered=False,
    )
    res = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1200000,
        new_price=1100000,
        old_lowest_price=1200000,
        alerts=[alert]
    )
    assert res.should_notify is False
    assert alert.is_triggered is False


def test_price_drop_alert(sample_product):
    alert = Alert(
        id=2,
        product_id=1,
        alert_type="PRICE_DROP",
        enabled=True,
    )
    res = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1300000,
        new_price=1200000,
        old_lowest_price=1200000,
        alerts=[alert]
    )
    assert res.should_notify is True
    assert any("Giá giảm" in r for r in res.reasons)


def test_price_increase_alert(sample_product):
    alert = Alert(
        id=3,
        product_id=1,
        alert_type="PRICE_INCREASE",
        enabled=True,
    )
    res = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1200000,
        new_price=1350000,
        old_lowest_price=1200000,
        alerts=[alert]
    )
    assert res.should_notify is True
    assert any("Giá tăng" in r for r in res.reasons)


def test_percent_drop_alert(sample_product):
    alert = Alert(
        id=4,
        product_id=1,
        alert_type="PERCENT_DROP",
        percentage=10.0,
        enabled=True,
    )
    # 1.000.000 -> 850.000 (15% drop >= 10%)
    res = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1000000,
        new_price=850000,
        old_lowest_price=1000000,
        alerts=[alert]
    )
    assert res.should_notify is True
    assert any("15.0%" in r for r in res.reasons)


def test_new_lowest_price_alert(sample_product):
    alert = Alert(
        id=5,
        product_id=1,
        alert_type="NEW_LOWEST_PRICE",
        enabled=True,
    )
    # Historical low was 1.200.000, new price is 1.150.000
    res = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1250000,
        new_price=1150000,
        old_lowest_price=1200000,
        alerts=[alert]
    )
    assert res.should_notify is True
    assert any("GIÁ THẤP NHẤT" in r for r in res.reasons)
