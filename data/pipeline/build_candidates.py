"""TourAPI 장소 + 영업시간 파싱 + 이동시간을 합쳐 웹이 읽는 candidates.json을 만든다.

이동시간은 out/travel.json(TMAP)이 있으면 그 값을, 없으면 직선거리 추정값을 쓰고
travel_source='estimate'로 표시한다. 화면은 추정값에 '약'과 안내 문구를 붙인다.

실행:
  uv run python -m pipeline.build_candidates            # 실데이터 (out/tourapi_places.json [+ out/travel.json])
  uv run python -m pipeline.build_candidates --sample   # 샘플 데이터 (API 키 없이 화면 확인용)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timedelta, timezone

import holidays

from pipeline.common import CONFIG, OUT, SAMPLE, WEB_DATA, load_yaml, read_json, write_json
from pipeline.fetch_tmap import estimate, haversine_m
from pipeline.parse_hours import parse

KST = timezone(timedelta(hours=9))

# 옛 서비스 분류(cat*) 코드. KorService2는 cat*를 비워 두고 분류체계(lclsSystm*)를 주므로
# 분류체계 이름(fetch_tourapi가 lclsSystmCode2로 붙인 lcls_names)과 장소명으로도 판단한다.
CAFE_CAT3 = {"A05020900"}  # 카페/전통찻집
EXPERIENCE_CAT2 = {"A0203"}  # 체험관광지
CAFE_WORDS = re.compile(r"카페|커피|찻집|다방|디저트|베이커리|제과")


def category(p: dict) -> str:
    ct = int(p["contenttypeid"])
    names = " ".join(p.get("lcls_names") or [])
    if ct == 39:
        is_cafe = p.get("cat3") in CAFE_CAT3 or CAFE_WORDS.search(names) or CAFE_WORDS.search(p.get("title", ""))
        return "cafe" if is_cafe else "food"
    if ct == 38:
        return "shopping"
    if ct == 28:
        return "experience"
    if ct == 14:
        return "culture"
    if ct == 12:
        return "experience" if p.get("cat2") in EXPERIENCE_CAT2 or "체험" in names else "sight"
    raise ValueError(f"지원하지 않는 contentTypeId {ct}")


def parse_spendtime(text: str) -> int | None:
    if not text:
        return None
    h = re.search(r"(\d+(?:\.\d+)?)\s*시간", text)
    m = re.search(r"(\d+)\s*분", text)
    if not h and not m:
        return None
    if re.search(r"~|이상|내외|\d\s*-\s*\d", text) and not re.search(r"약", text):
        return None  # 범위나 '이상'은 한 값으로 줄이지 않는다
    return round(float(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def same_sigungu(a: str, b: str) -> bool:
    """주소 앞 두 토큰(시도 시군구)이 같은지. 주소가 없으면 같다고 보지 않는다."""
    ta, tb = a.split()[:2], b.split()[:2]
    return len(ta) == 2 and ta == tb


def load_verified() -> dict[str, dict]:
    path = CONFIG / "verified.csv"
    with path.open(encoding="utf-8") as f:
        return {row["contentid"]: row for row in csv.DictReader(f) if row.get("contentid")}


def holiday_table(years: list[int]) -> dict[str, dict]:
    table = {}
    for d, name in sorted(holidays.KR(years=years).items()):
        kinds = ["public"]
        for key, word in (("seollal", "설날"), ("chuseok", "추석")):
            if word in name:
                kinds.append(f"{key}_period")
                if name == word:
                    kinds.append(f"{key}_day")
        table[d.isoformat()] = {"name": name, "kinds": kinds}
    return table


def build(sample: bool) -> dict:
    src = SAMPLE / "tourapi_places.sample.json" if sample else OUT / "tourapi_places.json"
    if not src.exists():
        hint = "uv run python -m pipeline.make_sample" if sample else "API 키가 필요합니다. uv run python -m pipeline.fetch_tourapi"
        sys.exit(f"{src.name} 없음 → {hint}")
    data = read_json(src)
    origin = data["origin"]
    travel_path = OUT / "travel.json"
    travel = read_json(travel_path)["travel"] if not sample and travel_path.exists() else {}
    dwell_cfg = load_yaml("dwell_minutes.yaml")
    verified = load_verified()

    candidates = []
    for p in data["places"]:
        v = verified.get(p["contentid"])
        use, rest = (v["usetime"], v["restdate"]) if v and v.get("usetime") else (p["usetime"], p["restdate"])
        parsed = parse(use, rest).to_json()
        cat = category(p)

        if v and v.get("dwell_min"):
            dwell, dwell_src = int(v["dwell_min"]), "verified"
        elif cat == "culture" and parse_spendtime(p.get("spendtime", "")):
            dwell, dwell_src = parse_spendtime(p["spendtime"]), "tourapi:spendtime"
        else:
            dwell, dwell_src = int(dwell_cfg[cat]), f"default:{cat}"

        if p["contentid"] in travel:
            tr, tr_src = travel[p["contentid"]], "tmap"
        else:
            tr, tr_src = estimate(origin["lat"], origin["lng"], p["lat"], p["lng"]), "estimate"
        straight = haversine_m(origin["lat"], origin["lng"], p["lat"], p["lng"])
        if straight > origin["radius_m"]["walk"]:
            tr = {k: val for k, val in tr.items() if k != "walk"}
        elif tr_src == "estimate" and not same_sigungu(origin.get("addr", ""), p.get("addr", "")):
            # 두물머리는 강으로 둘러싸여 있어 다른 시군(예: 강 건너 남양주 조안면)은 직선거리보다 훨씬 돌아간다.
            # 경로 없이 추정할 때는 도보 추천에서 뺀다(TMAP 경로가 있으면 그 값을 쓴다).
            tr = {k: val for k, val in tr.items() if k != "walk"}

        candidates.append({
            "id": f"tourapi:{p['contentid']}" if not sample else p["contentid"],
            "name": p["title"],
            "category": cat,
            "content_type_id": int(p["contenttypeid"]),
            "lat": p["lat"], "lng": p["lng"],
            "addr": p.get("addr", ""), "tel": p.get("tel", ""),
            "hours": {
                **parsed,
                "raw_usetime": use, "raw_restdate": rest,
                "source": "verified" if v and v.get("usetime") else ("sample" if sample else "tourapi"),
                "verified_on": v.get("verified_on") if v else None,
            },
            "dwell_min": dwell, "dwell_source": dwell_src,
            "travel": tr, "travel_source": tr_src,
            "attribution": "샘플 데이터(가상)" if sample else "한국관광공사 TourAPI",
        })

    n_est = sum(c["travel_source"] == "estimate" for c in candidates)
    travel_mode = "estimate" if n_est == len(candidates) else ("tmap" if n_est == 0 else "mixed")
    if not sample and n_est:
        print(f"이동시간 {n_est}곳은 직선거리 추정값입니다 (TMAP API 키가 필요합니다: fetch_tmap)", file=sys.stderr)

    today = datetime.now(KST).date()
    return {
        "mode": "sample" if sample else "live",
        "travel_mode": travel_mode,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "origin": origin,
        "candidates": sorted(candidates, key=lambda c: c["id"]),
        "holidays": holiday_table([today.year, today.year + 1]),
        "assumptions": {"dwell_minutes": dwell_cfg},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="샘플 데이터로 빌드 (API 키 없이)")
    args = ap.parse_args()
    result = build(args.sample)
    write_json(WEB_DATA / "candidates.json", result)
    write_json(OUT / "candidates.json", result)
    counts: dict[str, int] = {}
    for c in result["candidates"]:
        counts[c["hours"]["parse_status"]] = counts.get(c["hours"]["parse_status"], 0) + 1
    print(f"[{result['mode']}] 후보 {len(result['candidates'])}곳, 영업시간 해석 {counts} → web/public/data/candidates.json")


if __name__ == "__main__":
    main()
