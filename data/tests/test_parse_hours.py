import json
from pathlib import Path

import pytest

from pipeline.parse_hours import DAYS, parse

CASES = json.loads((Path(__file__).parent / "fixtures" / "hours_cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case):
    result = parse(case["usetime"], case["restdate"]).to_json()
    assert result["parse_status"] == case["status"], result["issues"]

    period = result["periods"][0]["weekly"] if result["periods"] else {}
    for day in DAYS + ["hol"]:
        if day in case:
            if case[day] is None:
                assert period.get(day) is None or day in result["closed"]["weekdays"]
            else:
                assert period.get(day) == case[day], (day, period)
    for key in ("last_entry", "last_entry_before_close_min"):
        if key in case:
            assert result[key] == case[key]
    if "periods" in case:
        assert len(result["periods"]) == case["periods"]
    for key in ("weekdays", "holidays", "dates", "monthly", "holiday_shift"):
        ck = f"closed_{key}" if key != "holiday_shift" else key
        if ck in case:
            assert result["closed"][key] == case[ck], (key, result["closed"])


def test_status_never_ok_without_hours():
    assert parse(None, None).status == "fail"


def test_seasonal_months_cover_year():
    r = parse("하절기(3월~10월) 09:00~18:00<br>동절기(11월~2월) 09:00~17:00", "연중무휴")
    months = sorted(m for p in r.periods for m in p.months)
    assert months == list(range(1, 13))
    winter = next(p for p in r.periods if 12 in p.months)
    assert winter.weekly["mon"] == [(540, 1020)]
