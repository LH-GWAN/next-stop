"""TMAP 경로 API로 출발지 ↔ 후보 이동시간을 계산한다.

도보: POST /tmap/routes/pedestrian?version=1 (도보 반경 안 후보만)
차량: POST /tmap/routes?version=1 (갈 때·올 때 모두 호출)
응답 features[0].properties.totalTime(초), totalDistance(m)를 쓴다.
원응답은 raw/tmap/ 에 저장하고 결과는 out/travel.json 에 쓴다.

실행: uv run python -m pipeline.fetch_tmap
"""

from __future__ import annotations

import math
import time

import httpx

from pipeline.common import OUT, RAW, read_json, require_key, write_json

BASE = "https://apis.openapi.sk.com/tmap"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def estimate(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    """TMAP 키가 없을 때 쓰는 추정값: 직선거리 × 1.3, 도보 67m/분(시속 4km), 차량 500m/분 + 2분.
    build_candidates가 travel_source='estimate'로 표시하고, 화면은 '약'과 안내 문구를 붙인다."""
    d = haversine_m(lat1, lng1, lat2, lng2) * 1.3
    walk = math.ceil(d / 67)
    car = math.ceil(d / 500) + 2
    return {"walk": {"go": walk, "back": walk, "m": round(d)}, "car": {"go": car, "back": car, "m": round(d)}}


class TMap:
    def __init__(self, key: str):
        self.client = httpx.Client(timeout=20, headers={"appKey": key, "Accept": "application/json"})

    def route(self, mode: str, a: dict, b: dict, tag: str) -> dict:
        cache = RAW / "tmap" / f"{mode}_{tag}.json"
        if cache.exists():
            body = read_json(cache)
        else:
            path = "/routes/pedestrian" if mode == "walk" else "/routes"
            payload = {
                "startX": str(a["lng"]), "startY": str(a["lat"]),
                "endX": str(b["lng"]), "endY": str(b["lat"]),
                "startName": a["name"], "endName": b["name"],
                "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO",
            }
            r = self.client.post(f"{BASE}{path}", params={"version": 1}, json=payload)
            if r.status_code != 200:
                raise RuntimeError(f"TMAP {mode} 오류 {r.status_code}: {r.text[:200]}")
            body = r.json()
            write_json(cache, body)
            time.sleep(0.25)
        props = body["features"][0]["properties"]
        return {"sec": int(props["totalTime"]), "m": int(props["totalDistance"])}


def main() -> None:
    tmap = TMap(require_key("TMAP_APP_KEY"))
    data = read_json(OUT / "tourapi_places.json")
    origin = {**data["origin"], "name": data["origin"]["name"]}
    walk_r = origin["radius_m"]["walk"]
    travel = {}
    for p in data["places"]:
        dest = {"lat": p["lat"], "lng": p["lng"], "name": p["title"]}
        entry: dict = {}
        if haversine_m(origin["lat"], origin["lng"], p["lat"], p["lng"]) <= walk_r:
            w = tmap.route("walk", origin, dest, f"{p['contentid']}_go")
            mins = math.ceil(w["sec"] / 60)
            entry["walk"] = {"go": mins, "back": mins, "m": w["m"]}
        go = tmap.route("car", origin, dest, f"{p['contentid']}_go")
        back = tmap.route("car", dest, origin, f"{p['contentid']}_back")
        g, b = math.ceil(go["sec"] / 60), math.ceil(back["sec"] / 60)
        # 차이가 20%를 넘으면 두 방향 모두 큰 값으로 보수적으로 잡는다
        if max(g, b) > 1.2 * min(g, b):
            g = b = max(g, b)
        entry["car"] = {"go": g, "back": b, "m": go["m"]}
        travel[p["contentid"]] = entry
    write_json(OUT / "travel.json", {"source": "tmap", "travel": travel})
    print(f"이동시간 계산 완료: {len(travel)}곳 → out/travel.json")


if __name__ == "__main__":
    main()
