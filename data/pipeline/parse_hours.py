"""TourAPI 자유 텍스트 영업시간·쉬는 날을 구조화한다.

원칙: 확실히 해석한 것만 구조화한다. 해석하지 못한 조각이 있으면 parse_status를
partial 또는 fail로 두고, 추천 엔진은 ok가 아닌 곳을 추천하지 않는다.

시각은 자정 기준 분(int)으로 다루고, 직렬화할 때 "HH:MM" 문자열로 바꾼다.
익일 새벽까지 영업하면 24:00을 넘는 값(예: 26:00)으로 표현한다.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_KO = {"월": "mon", "화": "tue", "수": "wed", "목": "thu", "금": "fri", "토": "sat", "일": "sun"}
ALL_MONTHS = list(range(1, 13))

# ---------------------------------------------------------------- 정규화

_DASHES = "∼〜～–—―-"


def clean(text: str | None) -> str:
    if not text:
        return ""
    t = html.unescape(text)
    t = re.sub(r"<\s*br\s*/?\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.translate({ord(c): "~" for c in _DASHES})
    t = t.replace("：", ":").replace("，", ",").replace("·", ",").replace("ㆍ", ",").replace("、", ",")
    t = re.sub(r"[ \t ]+", " ", t)
    return t.strip()


# ---------------------------------------------------------------- 시각

_TIME = r"(?:(오전|오후|새벽|밤)\s*)?(\d{1,2})\s*(?::\s*(\d{2})|시\s*(?:(\d{1,2})\s*분|반)?)"
TIME_RE = re.compile(_TIME)
RANGE_RE = re.compile(_TIME + r"\s*(?:부터)?\s*~\s*(익일|다음\s*날|새벽)?\s*" + _TIME + r"(?:\s*까지)?")


def _to_min(ampm: str | None, h: str, m_colon: str | None, m_ko: str | None, half: bool = False) -> int:
    hour = int(h)
    minute = int(m_colon or m_ko or (30 if half else 0))
    if ampm in ("오후", "밤") and hour < 12:
        hour += 12
    if ampm == "오전" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _range_from_match(m: re.Match) -> tuple[int, int]:
    g = m.groups()
    start = _to_min(g[0], g[1], g[2], g[3], half="반" in m.group(0).split("~")[0])
    end_raw = m.group(0).split("~", 1)[1]
    end = _to_min(g[5], g[6], g[7], g[8], half=bool(re.search(r"\d\s*시\s*반", end_raw)))
    next_day = bool(g[4])
    if next_day or end <= start:
        end += 24 * 60
    return start, end


def fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------- 요일 표현

_DAYSET_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"주말\s*(?:및|,|/)?\s*공휴일|토\s*,?\s*일\s*(?:요일)?\s*(?:및|,|/)?\s*공휴일"), ["sat", "sun", "hol"]),
    (re.compile(r"평일|월\s*~\s*금(?:요일)?"), ["mon", "tue", "wed", "thu", "fri"]),
    (re.compile(r"주말|토\s*[,~/]\s*일(?:요일)?|토\s*일요일"), ["sat", "sun"]),
    (re.compile(r"공휴일"), ["hol"]),
    (re.compile(r"매일|연중|상시|전일"), DAYS),
]


def _dayset(segment: str) -> list[str] | None:
    """조각 앞머리의 요일 한정어를 찾는다. 없으면 None(= 모든 요일)."""
    head = TIME_RE.split(segment, maxsplit=1)[0]
    for pat, days in _DAYSET_PATTERNS:
        if pat.search(head):
            return days
    days: list[str] = []
    for m in _DAY_RANGE_RE.finditer(head):
        days += [d for d in _day_range(m.group(1), m.group(2)) if d not in days]
    head = _DAY_RANGE_RE.sub(" ", head)
    days += [DAY_KO[s] for s in re.findall(r"([월화수목금토일])요일", head) if DAY_KO[s] not in days]
    return days or None


# '월~금', '월요일~목요일' 모두 받는다
_DAY_RANGE_RE = re.compile(r"([월화수목금토일])(?:요일)?\s*~\s*([월화수목금토일])(?:요일)?")


def _day_range(a: str, b: str) -> list[str]:
    i, j = DAYS.index(DAY_KO[a]), DAYS.index(DAY_KO[b])
    return DAYS[i : j + 1] if i <= j else DAYS[i:] + DAYS[: j + 1]


# ---------------------------------------------------------------- 결과 구조


@dataclass
class Period:
    months: list[int]
    weekly: dict[str, list[tuple[int, int]] | None]


@dataclass
class ParsedHours:
    periods: list[Period] = field(default_factory=list)
    last_entry: int | None = None
    last_entry_before_close_min: int | None = None
    closed_weekdays: list[str] = field(default_factory=list)
    holiday_shift: bool = False
    closed_holidays: list[str] = field(default_factory=list)
    closed_dates: list[str] = field(default_factory=list)
    closed_monthly: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    status: str = "fail"

    def to_json(self) -> dict:
        return {
            "periods": [
                {
                    "months": p.months,
                    "weekly": {
                        d: (None if v is None else [[fmt(s), fmt(e)] for s, e in v]) for d, v in p.weekly.items()
                    },
                }
                for p in self.periods
            ],
            "last_entry": fmt(self.last_entry) if self.last_entry is not None else None,
            "last_entry_before_close_min": self.last_entry_before_close_min,
            "closed": {
                "weekdays": self.closed_weekdays,
                "holiday_shift": self.holiday_shift,
                "holidays": self.closed_holidays,
                "dates": self.closed_dates,
                "monthly": self.closed_monthly,
            },
            "parse_status": self.status,
            "issues": self.issues,
        }


# ---------------------------------------------------------------- 영업시간

_ALWAYS_RE = re.compile(r"24\s*시간|상시\s*(?:개방|이용|관람)|연중\s*(?:개방|상시)|항시\s*개방|제한\s*없음|자유\s*관람|상시$")
_UNKNOWN_RE = re.compile(r"문의|홈페이지|변동|상이|협의|예약제|사전\s*예약|별도\s*공지|확인\s*요망|부정기|비정기|일몰|일출")
_LAST_RE = re.compile(
    r"(?:라스트\s*오더|L\s*\.?\s*O\s*\.?|주문\s*마감|입장\s*마감|매표\s*마감|발권\s*마감|입장\s*시간\s*마감|마지막\s*입장|마지막\s*주문)"
    r"\s*[:\s]*\(?\s*" + _TIME,
    re.I,
)
_LAST_REL_RE = re.compile(
    r"(?:입장|매표|발권|주문)?\s*(?:마감|종료)?[^\n]{0,12}?(?:종료|마감)\s*(\d{1,2})\s*(시간|분)\s*전"
)
_LAST_AFTER_RE = re.compile(_TIME + r"\s*(?:라스트\s*오더|L\s*\.?\s*O\b|주문\s*마감|입장\s*마감)", re.I)
# '준비시간(평일)'처럼 요일 한정이 붙어도 모든 요일에서 뺀다(보수적으로 영업 시간을 줄이는 쪽)
_BREAK_RE = re.compile(
    r"(?:(?:평일|주말)\s*)?(?:브레이크\s*타임|break\s*time|휴게\s*시간|쉬는\s*시간|준비\s*시간)\s*(?:\([^)\d]*\))?\s*[:\s]*\(?\s*", re.I
)
_SEASON_RE = re.compile(r"(하절기|동절기|하계|동계|여름|겨울|성수기|비수기)")
_MONTH_RANGE_RE = re.compile(r"(\d{1,2})\s*월?\s*(?:\d{1,2}\s*일)?\s*~\s*(?:익년\s*)?(\d{1,2})\s*월")
_INLINE_CLOSED_RE = re.compile(r"\(?\s*(?:매주\s*)?([월화수목금토일](?:요일)?(?:\s*,\s*[월화수목금토일](?:요일)?)*)\s*(?:정기\s*)?휴\s*(?:무|관|일|업)\s*\)?")


def _months_between(a: int, b: int) -> list[int]:
    if a <= b:
        return list(range(a, b + 1))
    return list(range(a, 13)) + list(range(1, b + 1))


def _split_segments(text: str) -> list[str]:
    text = re.sub(r"\[[^\]\n]*\]", lambda m: m.group(0).replace("/", ","), text)
    text = re.sub(r"(요일)\s*/\s*(?=[월화수목금토일]요일)", r"\1, ", text)
    parts = re.split(r"\n|/|;|\|", text)
    return [p.strip(" ,~") for p in parts if p.strip(" ,~")]


def parse_usetime(raw: str | None, out: ParsedHours) -> None:
    text = clean(raw)
    if not text:
        out.issues.append("usetime 비어 있음")
        return

    # 마지막 입장·주문 시각
    lasts = list(_LAST_RE.finditer(text)) or list(_LAST_AFTER_RE.finditer(text))
    if lasts:
        # 평일·주말 등 여러 번 나오면 가장 이른 시각을 쓴다(늦게 도착하는 추천을 막는 쪽)
        out.last_entry = min(_to_min(*m.groups()[:4]) for m in lasts)
        for m in reversed(lasts):
            text = text[: m.start()] + " " * (m.end() - m.start()) + text[m.end() :]
    else:
        r = _LAST_REL_RE.search(text)
        if r:
            n = int(r.group(1))
            out.last_entry_before_close_min = n * 60 if r.group(2) == "시간" else n
            text = text[: r.start()] + text[r.end() :]

    # 브레이크 타임: 영업 구간에서 뺀다
    breaks: list[tuple[int, int]] = []
    for bm in list(_BREAK_RE.finditer(text)):
        rm = RANGE_RE.search(text, bm.end())
        if rm and rm.start() - bm.end() <= 3:
            breaks.append(_range_from_match(rm))
            text = text[: bm.start()] + " " * (rm.end() - bm.start()) + text[rm.end() :]

    # usetime 안에 섞인 휴무 요일
    for im in _INLINE_CLOSED_RE.finditer(text):
        for d in re.findall(r"([월화수목금토일])(?:요일)?", im.group(1)):
            if DAY_KO[d] not in out.closed_weekdays:
                out.closed_weekdays.append(DAY_KO[d])
    text = _INLINE_CLOSED_RE.sub(" ", text)

    if _ALWAYS_RE.search(text) and not RANGE_RE.search(text):
        out.periods.append(Period(ALL_MONTHS, {d: [(0, 24 * 60)] for d in DAYS}))
        return

    # 계절별 구분
    segments = _split_segments(text)
    seasonal: dict[tuple[int, ...], list[str]] = {}
    current_months: tuple[int, ...] = tuple(ALL_MONTHS)
    season_without_months = False
    for seg in segments:
        mr = _MONTH_RANGE_RE.search(seg)
        if mr:
            current_months = tuple(_months_between(int(mr.group(1)), int(mr.group(2))))
            seg = seg[: mr.start()] + seg[mr.end() :]
        elif _SEASON_RE.search(seg):
            season_without_months = True
        seasonal.setdefault(current_months, []).append(seg)

    if season_without_months:
        out.issues.append("계절 구분이 있으나 기간(월)이 없음")

    for months, segs in seasonal.items():
        weekly: dict[str, list[tuple[int, int]] | None] = {d: None for d in DAYS}
        found = False
        header_days: list[str] | None = None
        for seg in segs:
            hm = re.fullmatch(r"\[([^\]]*)\]", seg)
            if hm:
                header_days = _dayset(hm.group(1))
                if header_days is None and not re.fullmatch(r"\s*(?:이용|운영|영업|관람)\s*시간\s*", hm.group(1)):
                    header_days = []  # '[교육시간]' 등 영업시간이 아닌 머리말: 아래 줄은 쓰지 않는다
                continue
            if header_days == []:
                if RANGE_RE.search(seg) or TIME_RE.search(seg):
                    out.issues.append(f"영업시간이 아닌 구역: {seg[:30]}")
                continue
            ranges = [_range_from_match(rm) for rm in RANGE_RE.finditer(seg)]
            if not ranges:
                leftover = re.sub(r"[\s,.()\[\]※*\-:]", "", seg)
                if leftover and _UNKNOWN_RE.search(seg):
                    out.issues.append(f"해석 불가 문구: {seg[:30]}")
                elif leftover and not re.fullmatch(r"(?:하절기|동절기|하계|동계|매일|연중|이용시간|운영시간|영업시간|관람시간)+", leftover):
                    out.issues.append(f"해석 불가 문구: {seg[:30]}")
                continue
            if _UNKNOWN_RE.search(seg):
                out.issues.append(f"변동 가능 문구: {seg[:30]}")
            ranges = _subtract(ranges, breaks)
            days = _dayset(seg) or header_days or DAYS
            for d in days:
                weekly.setdefault(d, None)
                weekly[d] = (weekly[d] or []) + ranges
            found = True
        if found:
            # 요일 한정어로 hol만 지정되고 평일/주말 미지정인 경우는 None으로 남아 partial 처리됨
            out.periods.append(Period(list(months), weekly))

    if not out.periods and not out.issues:
        out.issues.append("영업시간 형식을 찾지 못함")


def _subtract(ranges: list[tuple[int, int]], breaks: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result = []
    for s, e in ranges:
        pieces = [(s, e)]
        for bs, be in breaks:
            nxt = []
            for ps, pe in pieces:
                if be <= ps or bs >= pe:
                    nxt.append((ps, pe))
                    continue
                if ps < bs:
                    nxt.append((ps, bs))
                if be < pe:
                    nxt.append((be, pe))
            pieces = nxt
        result.extend(pieces)
    return result


# ---------------------------------------------------------------- 쉬는 날

_NO_REST_RE = re.compile(r"^(?:연중\s*무휴|무휴|없음|휴무\s*없음|휴무일\s*없음|연중\s*개방|상시\s*개방|해당\s*없음|년중\s*무휴|365일)")
_NTH = {"첫째": 1, "첫": 1, "1": 1, "둘째": 2, "두째": 2, "2": 2, "셋째": 3, "3": 3, "넷째": 4, "4": 4, "다섯째": 5, "5": 5, "마지막": -1}


def parse_restdate(raw: str | None, out: ParsedHours) -> None:
    text = clean(raw)
    if not text:
        out.issues.append("restdate 비어 있음")
        return
    if _NO_REST_RE.search(text):
        rest = _NO_REST_RE.sub("", text)
        if not re.sub(r"[\s,.()※*\-]", "", rest) or re.fullmatch(r"\s*\(?(?:단,?\s*)?", rest):
            return
        text = rest

    t = text
    consumed = []

    irregular = re.search(r"부정기|비정기|격주|수시|임시", t)
    if irregular:
        out.issues.append(f"불규칙 휴무: {irregular.group(0)}")
        t = t.replace(irregular.group(0), " ")

    # 공휴일이면 다음 날 휴무 (대체 휴무)
    m = re.search(r"\(?\s*(?:단[,\s]*)?(?:[월화수목금토일]요일이?\s*)?(?:공휴일|법정\s*공휴일|국경일)(?:인|과\s*겹칠|이면|일\s*경우|과\s*겹치는|과\s*중복)[^)\n]*?(?:다음\s*날|익일|그\s*다음|평일)[^)\n]*\)?", t)
    if m:
        out.holiday_shift = True
        consumed.append(m.group(0))
        t = t.replace(m.group(0), " ")

    # 'X요일이 공휴일인 경우 다음 날/다음 평일/Y요일 휴무' → 대체 휴무
    m = re.search(
        r"\(?\s*(?:단[,\s]*)?[월화수목금토일]요일이?\s*(?:법정\s*)?공휴일(?:인|일|이면|과\s*겹칠)?\s*(?:경우|때|시)?[^)\n]*?"
        r"(?:다음\s*날|익일|다음의?\s*첫\s*번?째?\s*평일|다음\s*평일|[월화수목금토일]요일)\s*(?:휴무|휴관|휴업|휴점)[^)\n]*\)?",
        t,
    )
    if m:
        out.holiday_shift = True
        t = t.replace(m.group(0), " ")
    # '공휴일이면 정상 영업' 예외는 보수적으로 무시한다(쉬는 요일은 공휴일에도 쉰다고 본다)
    m = re.search(r"\(?\s*(?:단[,\s]*)?(?:[월화수목금토일]요일이?\s*)?공휴일(?:이|인|일)?\s*(?:[월화수목금토일]요일인?)?\s*(?:경우|시|때)?\s*정상\s*(?:영업|운영)\s*\)?", t)
    if m:
        t = t.replace(m.group(0), " ")
    m = re.search(r"\(?\s*(?:단[,\s]*)?[월화수목금토일]요일이?\s*공휴일\s*시?\s*정상\s*(?:영업|운영)\s*\)?", t)
    if m:
        t = t.replace(m.group(0), " ")

    # 매주 X요일~Y요일
    for mm in _DAY_RANGE_RE.finditer(t):
        for d in _day_range(mm.group(1), mm.group(2)):
            if d not in out.closed_weekdays:
                out.closed_weekdays.append(d)
    t = _DAY_RANGE_RE.sub(" ", t)

    # 명절
    both = re.search(r"(?:명절|설\s*(?:날)?\s*[,및과/]\s*추석)\s*(연휴|당일|전날|전일)?", t)
    if both:
        kind = "period" if both.group(1) == "연휴" else "day"
        if both.group(1) in ("전날", "전일"):
            out.issues.append("명절 전날 휴무는 날짜 규칙 미지원")
        for h in ("seollal", "chuseok"):
            out.closed_holidays.append(f"{h}_{kind}")
        t = t.replace(both.group(0), " ")
    for key, pat in (("seollal", r"설\s*(?:날)?(?!악)"), ("chuseok", r"추석")):
        mm = re.search(pat + r"\s*(연휴|당일|전날|전일)?", t)
        if mm:
            kind = "period" if mm.group(1) == "연휴" else "day"
            out.closed_holidays.append(f"{key}_{kind}")
            t = t.replace(mm.group(0), " ")

    # 신정 / 1월 1일
    if re.search(r"신정|1\s*월\s*1\s*일|1\.\s*1\.?(?!\d)", t):
        out.closed_dates.append("01-01")
        t = re.sub(r"신정|1\s*월\s*1\s*일|1\.\s*1\.?(?!\d)", " ", t)

    # 매월 n째 주 X요일
    for mm in re.finditer(r"(?:매월|매달)?\s*((?:(?:첫|둘|두|셋|넷|다섯|마지막)째?|[1-5])\s*(?:,\s*(?:(?:첫|둘|두|셋|넷|다섯|마지막)째?|[1-5]))*)\s*(?:째)?\s*주\s*([월화수목금토일])요일", t):
        for tok in re.split(r"\s*,\s*", mm.group(1)):
            tok = tok.strip()
            nth = _NTH.get(tok) or _NTH.get(tok.replace("째", "") + "째") or _NTH.get(tok.replace("째", ""))
            if nth:
                out.closed_monthly.append({"nth": nth, "weekday": DAY_KO[mm.group(2)]})
        t = t.replace(mm.group(0), " ")

    # 매주 X요일 (목록)
    for mm in re.finditer(r"(?:매주\s*)?([월화수목금토일])(?:요일)?(?=\s*(?:,|및|과|와|\s|휴|정기|$|\())", t):
        # '일요일'의 '일', '공휴일'의 '일' 오인식 방지
        start = mm.start(1)
        prev = t[start - 1] if start > 0 else ""
        if prev in ("휴", "관", "당", "무", "매", "휴") or prev.isdigit():
            if prev.isdigit():
                out.issues.append(f"날짜 지정 휴무 미지원: {t[max(0, start - 4) : start + 1]}")
            continue
        d = DAY_KO[mm.group(1)]
        if d not in out.closed_weekdays:
            out.closed_weekdays.append(d)
        t = t[: mm.start()] + " " * (mm.end() - mm.start()) + t[mm.end() :]

    # 공휴일 휴무
    if re.search(r"(?:법정\s*)?공휴일\s*(?:휴무|휴관|휴일)?", t):
        out.closed_holidays.append("public")
        t = re.sub(r"(?:법정\s*)?공휴일\s*(?:휴무|휴관|휴일)?", " ", t)

    leftover = re.sub(r"매주|매월|정기|휴무|휴관|휴일|휴업|휴점|및|요일|당일|연휴|기타|,|\.|\(|\)|※|\*|-|\s|~|/|:|단", "", t)
    if leftover:
        out.issues.append(f"쉬는 날 해석 불가: {leftover[:30]}")


# ---------------------------------------------------------------- 진입점


def parse(usetime: str | None, restdate: str | None) -> ParsedHours:
    out = ParsedHours()
    parse_usetime(usetime, out)
    parse_restdate(restdate, out)
    out.closed_holidays = sorted(set(out.closed_holidays))

    has_hours = bool(out.periods)
    unknown_days = any(v is None for p in out.periods for d, v in p.weekly.items() if d in DAYS and d not in out.closed_weekdays)
    if not has_hours:
        out.status = "fail"
    elif out.issues or unknown_days:
        if unknown_days:
            out.issues.append("영업시간이 없는 요일이 있음")
        out.status = "partial"
    else:
        out.status = "ok"
    # 계절 구간이 12개월을 다 덮지 않으면 partial
    covered = {m for p in out.periods for m in p.months}
    if has_hours and covered != set(ALL_MONTHS):
        out.issues.append("영업시간이 없는 달이 있음")
        out.status = "partial"
    return out
