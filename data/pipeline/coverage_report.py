"""candidates.json 커버리지 리포트: 유형별 후보 수, 영업시간 해석률, 이동시간 출처.

실행: uv run python -m pipeline.coverage_report
결과는 표준 출력과 out/coverage.json 에 남는다(서식4·발표 자료용).
"""

from __future__ import annotations

from collections import Counter, defaultdict

from pipeline.common import OUT, WEB_DATA, read_json, write_json

LABEL = {"cafe": "카페", "food": "음식점", "shopping": "쇼핑", "experience": "체험", "culture": "문화시설", "sight": "관광지"}


def main() -> None:
    data = read_json(WEB_DATA / "candidates.json")
    cands = data["candidates"]
    by_cat: dict[str, Counter] = defaultdict(Counter)
    issues = Counter()
    for c in cands:
        by_cat[c["category"]][c["hours"]["parse_status"]] += 1
        for i in c["hours"]["issues"]:
            issues[i.split(":")[0]] += 1
    total = Counter(c["hours"]["parse_status"] for c in cands)
    report = {
        "mode": data["mode"],
        "generated_at": data["generated_at"],
        "n_candidates": len(cands),
        "parse_status": dict(total),
        "parse_ok_rate": round(total["ok"] / len(cands), 3) if cands else 0,
        "by_category": {LABEL[k]: dict(v) for k, v in sorted(by_cat.items())},
        "travel_source": dict(Counter(c["travel_source"] for c in cands)),
        "walkable": sum(1 for c in cands if "walk" in c["travel"]),
        "dwell_source": dict(Counter(c["dwell_source"].split(":")[0] for c in cands)),
        "top_issues": issues.most_common(10),
    }
    write_json(OUT / "coverage.json", report)

    print(f"[{report['mode']}] 후보 {report['n_candidates']}곳 (도보권 {report['walkable']}곳)")
    print(f"영업시간 해석: {report['parse_status']} → 추천 가능 비율 {report['parse_ok_rate']:.0%}")
    for k, v in report["by_category"].items():
        print(f"  {k}: {v}")
    print("이동시간 출처:", report["travel_source"])
    print("이용시간 출처:", report["dwell_source"])
    print("해석 실패 사유 상위:", report["top_issues"])


if __name__ == "__main__":
    main()
