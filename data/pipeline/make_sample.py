"""API 키 없이 화면과 엔진을 확인하기 위한 샘플 데이터를 만든다.

- 장소 이름은 모두 가상('샘플 ○○')이다. 실제 업체의 영업정보처럼 보이지 않게 한다.
- 영업시간 원문은 TourAPI 형식을 본뜬 문장으로, 실제 파서를 그대로 거친다.
- 좌표는 두물머리 대략 좌표에서 떨어뜨린 가상 위치이고, 이동시간은 직선거리 추정값이다.
결과 형식은 fetch_tourapi.py 출력(out/tourapi_places.json)과 같다.

실행: uv run python -m pipeline.make_sample
"""

from __future__ import annotations

import math

from pipeline.common import SAMPLE, origin_config, write_json

# (이름, contentTypeId, cat3, 북쪽 m, 동쪽 m, usetime 원문, restdate 원문, spendtime)
PLACES = [
    ("샘플 강변 카페", 39, "A05020900", 250, 180, "10:00~21:00 (라스트오더 20:30)", "연중무휴", ""),
    ("샘플 연잎 찻집", 39, "A05020900", -320, 420, "11:00~19:00", "매주 화요일", ""),
    ("샘플 국수집", 39, "A05020100", 480, -260, "11:00~20:00 (브레이크타임 15:00~16:30)", "매주 월요일", ""),
    ("샘플 한정식", 39, "A05020100", 2600, 3100, "11:30~21:00<br>L.O 20:00", "명절 당일", ""),
    ("샘플 로컬푸드 직매장", 38, "A04010200", 700, 520, "09:00~19:00", "설날 및 추석 당일", ""),
    ("샘플 공예 소품점", 38, "A04010600", -150, 610, "평일 11:00~18:00 / 주말 및 공휴일 10:00~19:00", "매주 수요일", ""),
    ("샘플 도자기 체험공방", 12, "A02030400", 900, -700, "10:00~18:00 (입장마감 17:00)", "매주 월요일 (공휴일인 경우 다음 날 휴무)", ""),
    ("샘플 천연염색 체험장", 28, "A03021700", 3400, -2100, "하절기(3월~10월) 10:00~18:00<br>동절기(11월~2월) 10:00~17:00", "매주 화요일, 1월 1일", ""),
    ("샘플 작은 미술관", 14, "A02060500", 1100, 300, "10:00~18:00<br>※ 관람종료 1시간 전 입장마감", "매주 월요일, 1월 1일, 설날 및 추석 당일", "약 40분"),
    ("샘플 향토 전시관", 14, "A02060100", 5200, 4800, "09:00~18:00", "매주 월요일", "1시간"),
    ("샘플 강변 산책 정원", 12, "A01010500", -600, -350, "상시 개방", "연중무휴", ""),
    ("샘플 전망 쉼터", 12, "A01010400", 1400, -1500, "09:00~18:00", "", ""),
    ("샘플 빵집", 39, "A05020900", 380, -90, "전화문의", "부정기", ""),
    ("샘플 수제 맥주집", 39, "A05020800", 4100, 2600, "17:00~익일 01:00", "매주 일요일", ""),
]


def offset(lat: float, lng: float, north_m: float, east_m: float) -> tuple[float, float]:
    dlat = north_m / 111_320
    dlng = east_m / (111_320 * math.cos(math.radians(lat)))
    return round(lat + dlat, 6), round(lng + dlng, 6)


def main() -> None:
    o = origin_config()
    origin = {
        "id": o["id"], "name": o["name"], "tourapi_contentid": None,
        "lat": o["lat"], "lng": o["lng"], "addr": "경기도 양평군 양서면 (대략 좌표)",
        "radius_m": o["radius_m"],
    }
    places = []
    for i, (name, ct, cat3, n, e, use, rest, spend) in enumerate(PLACES, start=1):
        lat, lng = offset(o["lat"], o["lng"], n, e)
        places.append({
            "contentid": f"sample-{i:02d}", "contenttypeid": ct, "title": name,
            "addr": "가상 주소 (샘플 데이터)", "tel": "", "lat": lat, "lng": lng,
            "dist_m": round(math.hypot(n, e)), "cat1": cat3[:3], "cat2": cat3[:5], "cat3": cat3,
            "lcls": ["", "", ""], "usetime": use, "restdate": rest, "spendtime": spend, "intro_keys": [],
        })
    write_json(SAMPLE / "tourapi_places.sample.json", {"source": "sample", "origin": origin, "places": places})
    print(f"샘플 {len(places)}곳 → sample/tourapi_places.sample.json")


if __name__ == "__main__":
    main()
