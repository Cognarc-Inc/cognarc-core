from datetime import UTC, datetime, timedelta, timezone

import pytest

from cognarc_core.clock import ManualClock, SystemClock


def test_system_clock_is_utc_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is UTC


def test_manual_clock_only_advances_on_demand() -> None:
    start = datetime(2026, 1, 1, 8, tzinfo=timezone(timedelta(hours=8)))
    clock = ManualClock(start)
    assert clock.now() == datetime(2026, 1, 1, 0, tzinfo=UTC)
    assert clock.now() == clock.now()
    assert clock.advance(90) == datetime(2026, 1, 1, 0, 1, 30, tzinfo=UTC)


def test_manual_clock_rejects_naive_start() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ManualClock(datetime(2026, 1, 1))
