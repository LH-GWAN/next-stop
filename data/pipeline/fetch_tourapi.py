"""TourAPI(KorService2)로 출발지 주변 후보를 수집한다.

1) searchKeyword2 로 출발지 좌표·contentid 확인 → out/origin.json
2) locationBasedList2 로 반경 안 후보 목록 (contentTypeId 12, 14, 28, 38, 39)
3) detailIntro2 로 유형별 이용시간·쉬는 날
4) lclsSystmCode2 로 분류체계 코드표(코드 → 이름). KorService2는 cat1~3 대신 lclsSystm1~3을 준다
원응답은 raw/tourapi/ 에 그대로 저장하고, 정규화 결과는 out/tourapi_places.json 에 쓴다.

실행: uv run python -m pipeline.fetch_tourapi
"""

from __future__ import annotations

import time

import httpx

from pipeline.common import OUT, RAW, origin_config, read_json, require_key, write_json

BASE = "https://apis.data.go.kr/B551011/KorService2"
CONTENT_TYPES = [12, 14, 28, 38, 39]

# detailIntro2 유형별 영업 필드. 실제 응답과 다르면 DATA_SOURCES.md와 함께 고친다.
INTRO_FIELDS = {
    12: {"usetime": "usetime", "restdate": "restdate"},
    14: {"usetime": "usetimeculture", "restdate": "restdateculture", "spendtime": "spendtime"},
    28: {"usetime": "usetimeleports", "restdate": "restdateleports"},
    38: {"usetime": "opentime", "restdate": "restdateshopping"},
    39: {"usetime": "opentimefood", "restdate": "restdatefood"},
}


class TourAPI:
    def __init__(self, key: str):
        self.key = key
        self.client = httpx.Client(timeout=20)

    def call(self, op: str, **params) -> list[dict]:
        cache = RAW / "tourapi" / f"{op}_{'_'.join(f'{k}-{v}' for k, v in sorted(params.items()))}.json"
        if cache.exists():
            body = read_json(cache)
        else:
            q = {"serviceKey": self.key, "MobileOS": "ETC", "MobileApp": "NextStop", "_type": "json", **params}
            r = self.client.get(f"{BASE}/{op}", params=q)
            r.raise_for_status()
            try:
                body = r.json()
            except ValueError as e:  # 키 오류 등은 XML로 온다
                raise RuntimeError(f"{op} 응답이 JSON이 아님: {r.text[:200]}") from e
            header = body.get("response", {}).get("header", {})
            if header.get("resultCode") not in ("0000", "00"):
                raise RuntimeError(f"{op} 오류: {header}")
            write_json(cache, body)
            time.sleep(0.15)
        items = body["response"]["body"].get("items") or {}
        item = items.get("item", []) if isinstance(items, dict) else []
        return item if isinstance(item, list) else [item]

    def paged(self, op: str, **params) -> list[dict]:
        out, page = [], 1
        while True:
            rows = self.call(op, numOfRows=100, pageNo=page, **params)
            out.extend(rows)
            if len(rows) < 100:
                return out
            page += 1


def lcls_code_names(api: TourAPI) -> dict[str, str]:
    """분류체계 전체 목록을 받아 코드 → 이름 표를 만든다. 응답 필드명이 달라도 *Cd/*Nm 쌍이면 읽는다."""
    names: dict[str, str] = {}
    for row in api.paged("lclsSystmCode2", lclsSystmListYn="Y"):
        for k, v in row.items():
            if k.endswith("Cd") and v and row.get(k[:-2] + "Nm"):
                names[str(v)] = row[k[:-2] + "Nm"]
        if row.get("code") and row.get("name"):
            names[str(row["code"])] = row["name"]
    return names


def main() -> None:
    api = TourAPI(require_key("TOURAPI_SERVICE_KEY"))
    origin = origin_config()

    hits = api.call("searchKeyword2", keyword=origin["keyword"], contentTypeId=12, numOfRows=10, pageNo=1)
    kw = origin["keyword"].replace(" ", "")
    pinned = [h for h in hits if str(h.get("contentid")) == str(origin.get("tourapi_contentid", ""))]
    named = [h for h in hits if h.get("title", "").replace(" ", "").endswith(kw)]  # '양평 두물머리' 등
    exact = pinned or sorted(named, key=lambda h: len(h.get("title", ""))) or hits
    if not exact:
        raise SystemExit(f"TourAPI에서 출발지 '{origin['keyword']}'를 찾지 못함")
    o = exact[0]
    origin_out = {
        "id": origin["id"], "name": origin["name"], "tourapi_contentid": o["contentid"],
        "lat": float(o["mapy"]), "lng": float(o["mapx"]), "addr": o.get("addr1", ""),
        "radius_m": origin["radius_m"],
    }
    write_json(OUT / "origin.json", origin_out)
    print(f"출발지: {o['title']} ({origin_out['lat']}, {origin_out['lng']})")

    radius = max(origin["radius_m"].values())
    places: dict[str, dict] = {}
    for ct in CONTENT_TYPES:
        rows = api.paged("locationBasedList2", mapX=origin_out["lng"], mapY=origin_out["lat"],
                         radius=radius, contentTypeId=ct, arrange="E")
        for row in rows:
            if row["contentid"] == o["contentid"]:
                continue
            places[row["contentid"]] = row
        print(f"contentTypeId {ct}: {len(rows)}곳")

    try:
        lcls_names = lcls_code_names(api)
    except RuntimeError as e:  # 코드표를 못 받아도 수집은 계속한다(범주는 장소명으로 판단)
        print(f"분류체계 코드표 조회 실패, 건너뜀: {e}")
        lcls_names = {}
    write_json(OUT / "lcls_codes.json", lcls_names)
    print(f"분류체계 코드 {len(lcls_names)}개")

    normalized = []
    for cid, row in places.items():
        ct = int(row["contenttypeid"])
        intro_rows = api.call("detailIntro2", contentId=cid, contentTypeId=ct)
        intro = intro_rows[0] if intro_rows else {}
        f = INTRO_FIELDS[ct]
        normalized.append({
            "contentid": cid,
            "contenttypeid": ct,
            "title": row.get("title", ""),
            "addr": row.get("addr1", ""),
            "tel": row.get("tel", ""),
            "lat": float(row["mapy"]),
            "lng": float(row["mapx"]),
            "dist_m": float(row.get("dist") or 0),
            "cat1": row.get("cat1", ""), "cat2": row.get("cat2", ""), "cat3": row.get("cat3", ""),
            "lcls": [row.get("lclsSystm1", ""), row.get("lclsSystm2", ""), row.get("lclsSystm3", "")],
            "lcls_names": [lcls_names.get(row.get(f"lclsSystm{i}", ""), "") for i in (1, 2, 3)],
            "usetime": intro.get(f["usetime"], ""),
            "restdate": intro.get(f["restdate"], ""),
            "spendtime": intro.get(f.get("spendtime", ""), "") if "spendtime" in f else "",
            "intro_keys": sorted(intro.keys()),
        })
    write_json(OUT / "tourapi_places.json", {"source": "tourapi", "origin": origin_out, "places": normalized})
    print(f"정규화 완료: {len(normalized)}곳 → out/tourapi_places.json")


if __name__ == "__main__":
    main()
