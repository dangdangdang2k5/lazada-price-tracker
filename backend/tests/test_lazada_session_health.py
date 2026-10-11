from app.services.lazada_session_health import LazadaSessionHealth


def test_session_becomes_unusable_only_after_consecutive_session_failures(tmp_path):
    health = LazadaSessionHealth(tmp_path / "health.json", failure_threshold=3)

    first = health.observe_failure("SESSION_EXPIRED", "login page")
    second = health.observe_failure("ANTI_BOT_CHALLENGE", "captcha")
    third = health.observe_failure("SESSION_EXPIRED", "login page")

    assert (first.state, first.failure_count, first.became_unusable) == ("DEGRADED", 1, False)
    assert (second.state, second.failure_count, second.became_unusable) == ("DEGRADED", 2, False)
    assert (third.state, third.failure_count, third.became_unusable) == ("UNUSABLE", 3, True)
    assert LazadaSessionHealth(tmp_path / "health.json", failure_threshold=3).snapshot()["state"] == "UNUSABLE"


def test_network_and_product_errors_do_not_expire_a_session(tmp_path):
    health = LazadaSessionHealth(tmp_path / "health.json", failure_threshold=3)

    update = health.observe_failure("NETWORK_BLOCKED", "timeout")

    assert update.state == "UNKNOWN"
    assert update.failure_count == 0
    assert update.counted_failure is False


def test_success_recovers_a_previously_unusable_session(tmp_path):
    health = LazadaSessionHealth(tmp_path / "health.json", failure_threshold=1)
    health.observe_failure("SESSION_EXPIRED", "login page")

    recovered = health.observe_success()

    assert recovered.state == "HEALTHY"
    assert recovered.recovered is True
    assert recovered.failure_count == 0
