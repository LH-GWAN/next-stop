# 데이터 출처와 계약

> TourAPI는 2026-09-26 실제 응답으로 확인했다(아래 2절). TMAP은 키가 없어 공개 문서 기준이며, 실제 응답과 다르면 실제 응답을 따르고 이 문서를 고친다.

## 1. 한국관광 데이터랩 (확보 완료)

- 메뉴: 지역별 분석 > 지역별 관광 현황, 월간 조회 2025.9.~2026.8.
- 파일: `data/raw/datalab/시군별_관광지표_202509-202608.csv` (147행, utf-8-sig)
- 기반 데이터: 이동통신(방문자·숙박·체류), 신용카드(관광소비), 내비게이션 TMAP(관광 목적지 검색량, 인기관광지)
- 방문자 수와 소비 금액은 데이터랩 안내에 따라 **상대 비교에만** 쓴다.
- CSV에 없는 조회값(코드에 상수로 적고 출처 주석): 양평군 업종별 관광소비 비중, 4개 시군의 숙박 목적지 검색 비중

### 선정 기준 수치 확인 결과

| 항목 | 값 |
|---|---|
| 검색량 상위 3분의 1(49곳) 컷오프 | 1,669천 건 |
| `데이터랩_분석_요약.md`의 컷오프 1,647천 건 적용 시 | 50곳 |
| 두 컷오프의 선정 결과 | 같음: 광명시, 양평군, 양산시, 구리시 |
| 중앙값 | 숙박방문자 비율 10.6%, 평균 체류시간 1,226분, 방문 1회당 관광소비 15,144원 |
| 양평군 순위 | 검색량 29위, 외지인 방문자 31위, 체류시간 짧은 순 26위 |

## 2. 한국관광공사 TourAPI (국문 관광정보 서비스, KorService2) — API 키가 필요합니다

- 기본 URL: `https://apis.data.go.kr/B551011/KorService2/`
- 공통 파라미터: `serviceKey, MobileOS=ETC, MobileApp=NextStop, _type=json, numOfRows, pageNo`
- 사용 오퍼레이션

| 오퍼레이션 | 용도 | 주요 파라미터 |
|---|---|---|
| `searchKeyword2` | 두물머리 좌표·contentid | `keyword`, `contentTypeId=12` |
| `locationBasedList2` | 반경 안 후보 | `mapX`(경도), `mapY`(위도), `radius`(m), `contentTypeId`, `arrange=E` |
| `detailIntro2` | 이용시간·쉬는 날 | `contentId`, `contentTypeId` |

- 수집 유형: 12 관광지, 14 문화시설, 28 레포츠, 38 쇼핑, 39 음식점
- `detailIntro2` 영업 필드(확인 필요)

| contentTypeId | 이용시간 | 쉬는 날 | 기타 |
|---|---|---|---|
| 12 관광지 | `usetime` | `restdate` | |
| 14 문화시설 | `usetimeculture` | `restdateculture` | `spendtime` |
| 28 레포츠 | `usetimeleports` | `restdateleports` | |
| 38 쇼핑 | `opentime` | `restdateshopping` | |
| 39 음식점 | `opentimefood` | `restdatefood` | |

- 매뉴얼 확인(2026-09-26, api.visitkorea.or.kr): 오퍼레이션과 위 필드명이 매뉴얼과 일치한다. 개발계정은 일 1,000건, 활용신청 후 약 10분 뒤 사용 가능.
- 범주 분류: KorService2 응답은 `cat1~3`이 비어 있고 분류체계 `lclsSystm1~3`을 준다(매뉴얼 응답 예시). 코드값은 API로만 조회되므로 `fetch_tourapi`가 `lclsSystmCode2`(`lclsSystmListYn=Y`)로 코드 → 이름 표를 받아 `lcls_names`로 붙이고, `category()`는 이름에 `카페·찻집` 등이 있거나 장소명에 `카페·커피` 등이 있으면 카페, 관광지 중 분류 이름에 `체험`이 있으면 체험으로 본다. 옛 `cat*` 코드가 오면 그것도 쓴다.
- 원응답은 `data/raw/tourapi/`에 저장(재현용, 기본은 git 제외).
- **실제 수집 결과(2026-09-26)**: 출발지는 키워드 검색 첫 결과가 '두물머리생태학교'라 `origins.yaml`에 '양평 두물머리'(contentid 128918)로 고정. 반경 10km 139곳(관광지 22, 문화시설 5, 레포츠 5, 쇼핑 3, 음식점 104), 분류체계 코드 315개. 영업시간 해석 ok 119(86%), partial 6, fail 14(원문 비어 있음 9곳, '전화 문의'·'점포별 상이' 등).
- 자주 나온 원문 형식(파서에 반영, `tests/fixtures/hours_cases.json`의 `real-*`): `- 마지막 주문 19:30`, `- 준비시간 15:00~16:00`, `[평일]`·`[주말]` 머리말, `월요일 / 수요일~금요일`, 쉬는 날 `매주 월요일~화요일`, `(단, 월요일이 공휴일인 경우 다음날 휴무)`. `공휴일이면 정상 영업` 예외는 보수적으로 무시(쉬는 요일은 공휴일에도 쉰다고 본다).
- 출처 표기: 모든 추천 카드와 푸터에 `한국관광공사 TourAPI`. 이미지는 공공누리 유형이 제각각이라 쓰지 않는다.

## 3. TMAP 경로 API (SK open API) — API 키가 필요합니다

- 도보: `POST https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1`
- 차량: `POST https://apis.openapi.sk.com/tmap/routes?version=1`
- 헤더 `appKey`, 본문 `startX, startY, endX, endY, startName, endName, reqCoordType=WGS84GEO`
- 응답 `features[0].properties.totalTime`(초), `totalDistance`(m)
- 도보는 두물머리 직선거리 1.5km 안 후보만, 차량은 갈 때·올 때 모두 호출. 두 방향 차이가 20%를 넘으면 큰 값으로 통일.
- **확인할 것**: 경로 결과를 미리 계산해 저장·배포해도 되는지 SK open API 약관. 안 되면 서버 라우트에서 요청 시 호출 + 짧은 캐시로 바꾼다.
- **추정 모드의 도보 제한**: 두물머리는 강으로 둘러싸여 강 건너(남양주 조안면 등)는 직선거리보다 훨씬 돌아간다. 추정값을 쓸 때는 출발지와 시군구가 다른 후보를 도보 추천에서 뺀다(차량만 남김).
- **키가 없으면(현재)** 직선거리 추정값(직선거리 × 1.3, 도보 67m/분, 차량 500m/분 + 2분)을 쓴다. 후보마다 `travel_source: "estimate"`, 데이터셋에 `travel_mode`를 남기고, 화면은 이동시간 앞에 `약`을 붙이고 "직선거리로 추정" 안내와 "TMAP API 키가 필요합니다"를 표시한다.

## 4. 온라인 설문 (31명, 서식4 수치만 사용)

코드는 설문 원자료를 다루지 않는다. 설문 수치는 서식4·발표 자료에만 쓰고 웹에는 옮기지 않는다.

## 5. 2025 국민여행조사

추가 소비의 의미 해석에만 쓴다(당일여행 1회 평균 지출 6만 9천 원, 숙박여행 22만 1천 원). 코드에서는 쓰지 않는다.
