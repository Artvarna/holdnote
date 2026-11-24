"""The demo snapshot's backup for London closes: when the London Stock
Exchange refuses the runner, Yahoo Finance's newest finished session is used,
marked as one source. No network here; the functions are pure."""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import demo_snapshot as ds  # noqa: E402


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def test_today_is_a_close_only_after_london_shuts():
    assert ds.finished("2026-11-23", at("2026-11-24T06:17"))
    assert not ds.finished("2026-11-24", at("2026-11-24T12:00"))
    assert ds.finished("2026-11-24", at("2026-11-24T17:05"))


def test_newest_session_both_funds_have():
    yahoo = {
        "IE00B3YLTY66": ({"2026-11-20": Decimal("13.1"), "2026-11-23": Decimal("13.2"),
                          "2026-11-24": Decimal("13.3")}, "USD", "u1"),
        # Yahoo leaves some finished sessions null: 23 Nov is missing here.
        "IE00B6YX5C33": ({"2026-11-20": Decimal("770"), "2026-11-24": Decimal("772")},
                         "USD", "u2"),
    }
    day, closes = ds.london_from_yahoo(yahoo, at("2026-11-24T12:00"))
    # 24 Nov is still trading at noon, 23 Nov is missing for SPY5: 20 Nov.
    assert day == "2026-11-20"
    assert closes["IE00B3YLTY66"] == (Decimal("13.1"), "USD", "u1")
    assert closes["IE00B6YX5C33"] == (Decimal("770"), "USD", "u2")


def test_no_common_session_stops_the_run():
    yahoo = {"A": ({"2026-11-20": Decimal("1")}, "USD", "u"),
             "B": ({"2026-11-23": Decimal("2")}, "USD", "u")}
    with pytest.raises(ds.Failed):
        ds.london_from_yahoo(yahoo, at("2026-11-24T06:17"))
