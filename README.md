# 다음 한 곳

관광객의 남은 시간을 지역 소비로 연결하는 모바일 웹. 두물머리(경기 양평군)에서 남은 시간·이동수단·관심 항목을 입력하면, `이동 + 이용 + 복귀 + 여유`가 남은 시간 안에 들어오면서 지금 영업 중인 곳 **한 곳**을 추천한다.

2026 한국관광 데이터랩 활용 경진대회 응모작 시제품.

## 현재 상태

- **TourAPI 연결 완료(2026-09-26).** 두물머리(TourAPI '양평 두물머리') 반경 10km 139곳, 영업시간 자동 해석 119곳(86%). 해석하지 못한 곳은 추천하지 않는다. 키가 없으면 가상 장소 14곳의 샘플 데이터로 동작한다.
- **TMAP 키가 필요합니다(선택).** 없으면 이동시간을 직선거리로 추정하고, 화면에 `약`과 추정 안내를 붙인다.
- 웹은 관광객이 쓰는 서비스 화면(입력·결과)만 둔다. 데이터랩 선정 근거·설문 등 응모 자료는 `docs/`와 `data/analysis/`에만 둔다.
- 테스트: Python 51개(영업시간 파서 45, 후보 빌드 6), TypeScript 29개(추천 엔진, 무작위 입력 1,000개 속성 테스트 포함).

## 구조

```
data/                 Python 3.12 + uv
  analysis/select_region.py   데이터랩 147개 시군 → 양평군 선정 재현 + 차트
  pipeline/fetch_tourapi.py   TourAPI(KorService2) 수집      ← TOURAPI_SERVICE_KEY 필요
  pipeline/fetch_tmap.py      TMAP 도보·차량 이동시간          ← TMAP_APP_KEY 필요(없으면 직선거리 추정)
  pipeline/parse_hours.py     자유 텍스트 영업시간 → 구조화
  pipeline/build_candidates.py  병합 → web/public/data/candidates.json
  pipeline/coverage_report.py   수집·해석 커버리지
  pipeline/make_sample.py     키 없이 쓰는 샘플 데이터
  config/                     출발지, 유형별 이용시간(가정값), 직접 확인한 영업정보(verified.csv)
web/                  Next.js 16 + TypeScript + Tailwind
  lib/engine/                 추천 엔진(순수 함수) + 테스트
  app/                        / 입력, /result 결과
docs/                 규칙·데이터 문서, 데이터랩 차트(응모 첨부용), 서식4 반영 문구
```

## 실행

```bash
cd data && uv sync && uv run pytest -q
```

데이터랩 원자료는 저장소에 없다. 한국관광 데이터랩(지역별 관광 현황, 2025.9.~2026.8.)에서 받아 `data/raw/datalab/시군별_관광지표_202509-202608.csv`로 둔 뒤 실행한다.

```bash
cd data && uv run python analysis/select_region.py
```

샘플 데이터로 빌드(키 없이):

```bash
cd data && uv run python -m pipeline.make_sample && uv run python -m pipeline.build_candidates --sample && uv run python -m pipeline.coverage_report
```

실데이터로 빌드(`.env`에 TourAPI 키를 넣은 뒤, TMAP 없이):

```bash
cd data && uv run python -m pipeline.fetch_tourapi && uv run python -m pipeline.build_candidates && uv run python -m pipeline.coverage_report
```

TMAP 키가 있으면 `fetch_tourapi` 다음에 `uv run python -m pipeline.fetch_tmap`을 실행한다. `out/travel.json`이 있으면 추정값 대신 TMAP 경로 시간을 쓴다.

웹:

```bash
cd web && npm install && npm test && npm run dev
```

시연용 시각 고정: `/?at=2026-10-10T15:00` (KST). 입력 화면 아래 `다른 시각 기준으로 찾기`에서도 고를 수 있다.

## 키 연결 후 할 일

1. `.env.example`을 `.env`로 복사하고 TourAPI 키를 넣는다(TMAP 키는 선택).
2. 위 실데이터 빌드를 실행한다. TMAP 결과가 없는 후보는 직선거리 추정값을 쓰고 `travel_source: "estimate"`로 표시된다.
3. `out/coverage.json`에서 영업시간 해석률을 확인하고, 원문을 보고 `data/tests/fixtures/hours_cases.json`에 실제 사례를 추가한다.
4. 추천 상위 후보는 전화로 영업시간을 확인해 `data/config/verified.csv`에 적는다.
5. `web/`을 Vercel에 배포한다(Root Directory: `web`). 선택: `NEXT_PUBLIC_REPORT_URL`에 오류 신고용 구글폼 주소를 넣으면 `정보가 틀려요` 링크가 켜진다.
