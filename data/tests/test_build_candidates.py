"""build_candidates: KorService2 분류체계 범주 판단과 TMAP 키 없는 실데이터 빌드."""

from pipeline import build_candidates as bc
from pipeline.common import write_json


def place(**kw) -> dict:
    base = {
        "contentid": "1", "contenttypeid": 39, "title": "양평 국수", "addr": "", "tel": "",
        "lat": 37.536, "lng": 127.320, "cat1": "", "cat2": "", "cat3": "",
        "lcls": ["", "", ""], "lcls_names": ["", "", ""],
        "usetime": "10:00~20:00", "restdate": "연중무휴", "spendtime": "",
    }
    return {**base, **kw}


def test_cafe_from_lcls_name():
    assert bc.category(place(lcls_names=["음식", "음식점", "카페/전통찻집"])) == "cafe"


def test_cafe_from_title_when_codes_empty():
    assert bc.category(place(title="두물머리 커피")) == "cafe"


def test_food_default():
    assert bc.category(place()) == "food"


def test_experience_from_lcls_name():
    assert bc.category(place(contenttypeid=12, lcls_names=["체험관광", "공예체험", ""])) == "experience"
    assert bc.category(place(contenttypeid=12, lcls_names=["자연관광", "", ""])) == "sight"


def test_legacy_cat_codes_still_work():
    assert bc.category(place(cat3="A05020900")) == "cafe"
    assert bc.category(place(contenttypeid=12, cat2="A0203")) == "experience"


def test_live_build_without_tmap_uses_estimate(tmp_path, monkeypatch):
    monkeypatch.setattr(bc, "OUT", tmp_path)
    origin = {"id": "o", "name": "출발", "lat": 37.5345, "lng": 127.3185, "addr": "경기도 양평군 양서면",
              "radius_m": {"walk": 1500, "car": 10000}}
    places = [place(addr="경기도 양평군 양서면 양수로 1"), place(contentid="2", addr="경기도 남양주시 조안면 북한강로 1")]
    write_json(tmp_path / "tourapi_places.json", {"source": "tourapi", "origin": origin, "places": places})
    result = bc.build(sample=False)
    assert result["mode"] == "live"
    assert result["travel_mode"] == "estimate"
    same, other = result["candidates"]
    assert same["travel_source"] == "estimate"
    assert same["attribution"] == "한국관광공사 TourAPI"
    assert same["travel"]["walk"]["go"] > 0
    # 추정 모드에서 다른 시군(강 건너)은 도보 후보에서 뺀다
    assert "walk" not in other["travel"] and "car" in other["travel"]
