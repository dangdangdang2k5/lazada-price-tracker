import datetime
from typing import List, Tuple, Optional
from app.core.logging import logger
from app.models.alert import Alert, AlertType
from app.models.product import Product
from app.utils.currency import format_currency


class AlertEvaluationResult:
    def __init__(self, should_notify: bool, reasons: List[str], target_price: Optional[int] = None):
        self.should_notify = should_notify
        self.reasons = reasons
        self.target_price = target_price


class AlertEngine:
    """
    Evaluates product alert conditions and manages anti-spam state transitions.
    """

    @staticmethod
    def evaluate_alerts(
        product: Product,
        old_price: int,
        new_price: int,
        old_lowest_price: int,
        alerts: List[Alert]
    ) -> AlertEvaluationResult:
        """
        Evaluate active alerts for a product against new and old prices.
        Mutates alert state attributes (is_triggered, last_triggered_price, last_triggered_at) in-place.
        """
        if new_price <= 0:
            return AlertEvaluationResult(should_notify=False, reasons=[])

        triggered_reasons: List[str] = []
        target_price_found: Optional[int] = None
        now = datetime.datetime.utcnow()

        for alert in alerts:
            if not alert.enabled:
                continue

            # 1. TARGET_PRICE
            if alert.alert_type == AlertType.TARGET_PRICE.value or alert.alert_type == "TARGET_PRICE":
                if alert.target_price is not None:
                    target_price_found = alert.target_price
                    if new_price <= alert.target_price:
                        if not alert.is_triggered:
                            # State transition: not triggered -> triggered
                            alert.is_triggered = True
                            alert.last_triggered_price = new_price
                            alert.last_triggered_at = now
                            triggered_reasons.append(
                                f"🎯 Đạt giá mục tiêu: {format_currency(new_price)} <= {format_currency(alert.target_price)}"
                            )
                            logger.info(
                                f"[ALERT TRIGGERED] Product '{product.name}' reached target price {alert.target_price} (Current: {new_price})"
                            )
                        else:
                            # Already triggered: Anti-spam suppression unless price fell further
                            if alert.last_triggered_price and new_price < alert.last_triggered_price:
                                alert.last_triggered_price = new_price
                                alert.last_triggered_at = now
                                triggered_reasons.append(
                                    f"🎯 Giá tiếp tục giảm sâu dưới mức mục tiêu: {format_currency(new_price)}"
                                )
                    else:
                        # Price is now above target -> reset state so future drop triggers again
                        if alert.is_triggered:
                            logger.info(
                                f"[ALERT RESET] Product '{product.name}' price {new_price} is above target {alert.target_price}. Resetting trigger state."
                            )
                            alert.is_triggered = False

            # 2. PRICE_DROP
            elif alert.alert_type == AlertType.PRICE_DROP.value or alert.alert_type == "PRICE_DROP":
                if old_price > 0 and new_price < old_price:
                    # Prevent duplicate notification if same price was already alerted
                    if alert.last_triggered_price != new_price:
                        alert.is_triggered = True
                        alert.last_triggered_price = new_price
                        alert.last_triggered_at = now
                        diff = old_price - new_price
                        pct = (diff / old_price) * 100
                        triggered_reasons.append(
                            f"📉 Giá giảm: -{format_currency(diff)} (-{pct:.1f}%)"
                        )
                        logger.info(f"[ALERT TRIGGERED] Product '{product.name}' price dropped by {diff} VND")

            # 3. PRICE_INCREASE
            elif alert.alert_type == AlertType.PRICE_INCREASE.value or alert.alert_type == "PRICE_INCREASE":
                if old_price > 0 and new_price > old_price:
                    if alert.last_triggered_price != new_price:
                        alert.is_triggered = True
                        alert.last_triggered_price = new_price
                        alert.last_triggered_at = now
                        diff = new_price - old_price
                        pct = (diff / old_price) * 100
                        triggered_reasons.append(
                            f"📈 Giá tăng: +{format_currency(diff)} (+{pct:.1f}%)"
                        )
                        logger.info(f"[ALERT TRIGGERED] Product '{product.name}' price increased by {diff} VND")

            # 4. PERCENT_DROP
            elif alert.alert_type == AlertType.PERCENT_DROP.value or alert.alert_type == "PERCENT_DROP":
                if alert.percentage is not None and alert.percentage > 0 and old_price > 0:
                    actual_drop_pct = ((old_price - new_price) / old_price) * 100
                    if actual_drop_pct >= alert.percentage:
                        if alert.last_triggered_price != new_price:
                            alert.is_triggered = True
                            alert.last_triggered_price = new_price
                            alert.last_triggered_at = now
                            triggered_reasons.append(
                                f"🔥 Giảm {actual_drop_pct:.1f}% (Mức yêu cầu >= {alert.percentage:.1f}%)"
                            )
                            logger.info(
                                f"[ALERT TRIGGERED] Product '{product.name}' dropped by {actual_drop_pct:.1f}% >= threshold {alert.percentage}%"
                            )

            # 5. NEW_LOWEST_PRICE
            elif alert.alert_type == AlertType.NEW_LOWEST_PRICE.value or alert.alert_type == "NEW_LOWEST_PRICE":
                if old_lowest_price > 0 and new_price < old_lowest_price:
                    if alert.last_triggered_price != new_price:
                        alert.is_triggered = True
                        alert.last_triggered_price = new_price
                        alert.last_triggered_at = now
                        triggered_reasons.append(
                            f"👑 GIÁ THẤP NHẤT TỪ TRƯỚC ĐẾN NAY! (Kỷ lục cũ: {format_currency(old_lowest_price)})"
                        )
                        logger.info(f"[ALERT TRIGGERED] Product '{product.name}' reached historical low {new_price}")

        should_notify = len(triggered_reasons) > 0
        return AlertEvaluationResult(
            should_notify=should_notify,
            reasons=triggered_reasons,
            target_price=target_price_found
        )
