import pytest
from app.models.product import Product
from app.models.alert import Alert
from app.services.alert_engine import AlertEngine


@pytest.fixture
def sample_product():
    return Product(
        id=1,
        name="Logitech G Pro",
        url="https://www.lazada.vn/products/logitech-g-pro-i123.html",
        current_price=1200000,
        lowest_price=1200000,
        highest_price=1500000,
    )


def test_anti_spam_prevents_duplicate_notifications(sample_product):
    """
    Scenario:
    Target: 1.000.000đ
    1. Check 1: Price drops to 950.000đ -> NOTIFY 1 time.
    2. Check 2 (5 mins later): Price remains 950.000đ -> DO NOT notify again.
    3. Check 3: Price rises to 1.050.000đ -> Reset trigger status.
    4. Check 4: Price drops back to 980.000đ -> NOTIFY again!
    """
    alert = Alert(
        id=1,
        product_id=1,
        alert_type="TARGET_PRICE",
        target_price=1000000,
        enabled=True,
        is_triggered=False,
    )

    # Step 1: Price drops to 950.000đ
    res1 = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1200000,
        new_price=950000,
        old_lowest_price=1200000,
        alerts=[alert]
    )
    assert res1.should_notify is True
    assert alert.is_triggered is True
    assert alert.last_triggered_price == 950000

    # Step 2: Next check, price is still 950.000đ -> Should NOT notify
    res2 = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=950000,
        new_price=950000,
        old_lowest_price=950000,
        alerts=[alert]
    )
    assert res2.should_notify is False
    assert alert.is_triggered is True

    # Step 3: Price rises above target to 1.050.000đ -> Alert trigger state should reset to False
    res3 = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=950000,
        new_price=1050000,
        old_lowest_price=950000,
        alerts=[alert]
    )
    assert res3.should_notify is False
    assert alert.is_triggered is False

    # Step 4: Price drops again below target to 980.000đ -> Should NOTIFY again!
    res4 = AlertEngine.evaluate_alerts(
        product=sample_product,
        old_price=1050000,
        new_price=980000,
        old_lowest_price=950000,
        alerts=[alert]
    )
    assert res4.should_notify is True
    assert alert.is_triggered is True
    assert alert.last_triggered_price == 980000
