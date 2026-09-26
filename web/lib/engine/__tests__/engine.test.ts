import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { bufferFor } from "../config";
import { checkOpen } from "../hours";
import { recommend } from "../recommend";
import { addMin, parseKstLocal } from "../time";
import type { Candidate, Dataset, Hours, Interest, Mode } from "../types";

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

function hours(ranges: [string, string][], over: Partial<Hours> = {}, closed: Partial<Hours["closed"]> = {}): Hours {
  return {
    periods: [{ months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], weekly: Object.fromEntries(DAYS.map((d) => [d, ranges])) }],
    last_entry: null,
    last_entry_before_close_min: null,
    closed: { weekdays: [], holiday_shift: false, holidays: [], dates: [], monthly: [], ...closed },
    parse_status: "ok",
    issues: [],
    raw_usetime: "",
    raw_restdate: "",
    source: "tourapi",
    verified_on: null,
    ...over,
  };
}

function cand(id: string, over: Partial<Candidate> = {}): Candidate {
  return {
    id,
    name: id,
    category: "cafe",
    content_type_id: 39,
    lat: 0,
    lng: 0,
    addr: "",
    tel: "",
    hours: hours([["09:00", "22:00"]]),
    dwell_min: 20,
    dwell_source: "default:cafe",
    travel: { walk: { go: 10, back: 10, m: 700 }, car: { go: 4, back: 4, m: 700 } },
    travel_source: "tmap",
    attribution: "한국관광공사 TourAPI",
    ...over,
  };
}

const HOLIDAYS: Dataset["holidays"] = {
  "2026-09-24": { name: "추석 전날", kinds: ["public", "chuseok_period"] },
  "2026-09-25": { name: "추석", kinds: ["public", "chuseok_period", "chuseok_day"] },
  "2026-09-26": { name: "추석 다음날", kinds: ["public", "chuseok_period"] },
  "2026-10-03": { name: "개천절", kinds: ["public"] },
  "2026-10-05": { name: "개천절 대체 휴일", kinds: ["public"] },
};

function ds(candidates: Candidate[]): Dataset {
  return {
    mode: "sample",
    generated_at: "",
    origin: { id: "o", name: "두물머리", lat: 0, lng: 0, addr: "" },
    candidates,
    holidays: HOLIDAYS,
  };
}

const at = (s: string) => parseKstLocal(s)!;
const WED_15 = at("2026-10-07T15:00");

describe("여유 시간", () => {
  it.each([
    [20, 10],
    [30, 10],
    [50, 10],
    [60, 12],
    [90, 18],
    [120, 24],
  ])("남은 %i분 → 여유 %i분", (t, b) => expect(bufferFor(t)).toBe(b));
});

describe("서식4 예시", () => {
  it("남은 50분 = 이동 10 + 이용 20 + 복귀 10 + 여유 10 이면 추천된다", () => {
    const r = recommend({ remainingMin: 50, mode: "walk", interests: [], now: WED_15 }, ds([cand("a")]));
    expect(r.pick?.candidate.id).toBe("a");
    expect(r.pick?.total).toBe(50);
    expect(r.pick?.slack).toBe(10);
  });
  it("1분이라도 넘으면 추천하지 않는다", () => {
    const c = cand("a", { dwell_min: 21 });
    const r = recommend({ remainingMin: 50, mode: "walk", interests: [], now: WED_15 }, ds([c]));
    expect(r.pick).toBeNull();
    expect(r.counts.too_long).toBe(1);
    // 51분이면 여유가 ceil(10.2)=11분이 되어 41+11=52 > 51, 52분부터 가능
    expect(r.nearMiss?.neededMin).toBe(52);
  });
});

describe("영업 판정", () => {
  const h = hours([["10:00", "18:00"]]);
  it("떠나는 시각이 마감 전이면 열림", () => {
    expect(checkOpen(h, at("2026-10-07T17:30"), at("2026-10-07T17:55"), HOLIDAYS).open).toBe(true);
  });
  it("머무는 중에 마감되면 제외", () => {
    const r = checkOpen(h, at("2026-10-07T17:30"), at("2026-10-07T18:15"), HOLIDAYS);
    expect(r.open).toBe(false);
  });
  it("개점 전 도착은 제외", () => {
    expect(checkOpen(h, at("2026-10-07T09:50"), at("2026-10-07T10:20"), HOLIDAYS).open).toBe(false);
  });
  it("마지막 입장 이후 도착은 제외", () => {
    const le = hours([["10:00", "18:00"]], { last_entry: "17:00" });
    expect(checkOpen(le, at("2026-10-07T17:05"), at("2026-10-07T17:30"), HOLIDAYS).reason).toBe("after_last_entry");
    expect(checkOpen(le, at("2026-10-07T16:55"), at("2026-10-07T17:30"), HOLIDAYS).open).toBe(true);
  });
  it("'마감 1시간 전 입장마감'도 반영", () => {
    const rel = hours([["10:00", "18:00"]], { last_entry_before_close_min: 60 });
    expect(checkOpen(rel, at("2026-10-07T17:10"), at("2026-10-07T17:40"), HOLIDAYS).open).toBe(false);
  });
  it("정기 휴무 요일은 제외", () => {
    const monClosed = hours([["10:00", "18:00"]], {}, { weekdays: ["mon"] });
    expect(checkOpen(monClosed, at("2026-09-28T12:00"), at("2026-09-28T12:30"), HOLIDAYS).reason).toBe("closed_day");
    expect(checkOpen(monClosed, at("2026-09-29T12:00"), at("2026-09-29T12:30"), HOLIDAYS).open).toBe(true);
  });
  it("추석 당일 휴무", () => {
    const c = hours([["10:00", "18:00"]], {}, { holidays: ["chuseok_day"] });
    expect(checkOpen(c, at("2026-09-25T12:00"), at("2026-09-25T12:30"), HOLIDAYS).open).toBe(false);
    expect(checkOpen(c, at("2026-09-26T12:00"), at("2026-09-26T12:30"), HOLIDAYS).open).toBe(true);
  });
  it("휴무 요일이 공휴일이면 열고 다음 날 쉰다", () => {
    const c = hours([["10:00", "18:00"]], {}, { weekdays: ["mon"], holiday_shift: true });
    expect(checkOpen(c, at("2026-10-05T12:00"), at("2026-10-05T12:30"), HOLIDAYS).open).toBe(true);
    expect(checkOpen(c, at("2026-10-06T12:00"), at("2026-10-06T12:30"), HOLIDAYS).open).toBe(false);
  });
  it("매월 둘째 주 화요일 휴무", () => {
    const c = hours([["10:00", "18:00"]], {}, { monthly: [{ nth: 2, weekday: "tue" }] });
    expect(checkOpen(c, at("2026-10-13T12:00"), at("2026-10-13T12:30"), HOLIDAYS).open).toBe(false);
    expect(checkOpen(c, at("2026-10-06T12:00"), at("2026-10-06T12:30"), HOLIDAYS).open).toBe(true);
  });
  it("1월 1일 휴무", () => {
    const c = hours([["10:00", "18:00"]], {}, { dates: ["01-01"] });
    expect(checkOpen(c, at("2027-01-01T12:00"), at("2027-01-01T12:30"), {}).open).toBe(false);
  });
  it("익일 새벽까지 영업하면 새벽 도착도 열림", () => {
    const c = hours([["17:00", "26:00"]]);
    expect(checkOpen(c, at("2026-10-08T01:00"), at("2026-10-08T01:40"), HOLIDAYS).open).toBe(true);
    expect(checkOpen(c, at("2026-10-08T01:40"), at("2026-10-08T02:20"), HOLIDAYS).open).toBe(false);
  });
  it("공휴일 영업시간(hol)을 따로 쓴다", () => {
    const c = hours([["11:00", "18:00"]]);
    c.periods[0].weekly.hol = [["10:00", "19:00"]];
    expect(checkOpen(c, at("2026-10-05T10:15"), at("2026-10-05T10:40"), HOLIDAYS).open).toBe(true);
    expect(checkOpen(c, at("2026-10-07T10:15"), at("2026-10-07T10:40"), HOLIDAYS).open).toBe(false);
  });
  it("계절별 시간: 11월에는 동절기 마감", () => {
    const c = hours([]);
    c.periods = [
      { months: [3, 4, 5, 6, 7, 8, 9, 10], weekly: Object.fromEntries(DAYS.map((d) => [d, [["10:00", "18:00"]]])) },
      { months: [11, 12, 1, 2], weekly: Object.fromEntries(DAYS.map((d) => [d, [["10:00", "17:00"]]])) },
    ];
    expect(checkOpen(c, at("2026-10-07T17:10"), at("2026-10-07T17:40"), HOLIDAYS).open).toBe(true);
    expect(checkOpen(c, at("2026-11-04T17:10"), at("2026-11-04T17:40"), HOLIDAYS).open).toBe(false);
  });
});

describe("추천 규칙", () => {
  it("영업시간을 해석하지 못한 곳은 추천하지 않는다", () => {
    const bad = cand("a", { hours: { ...hours([["00:00", "24:00"]]), parse_status: "partial" } });
    const r = recommend({ remainingMin: 90, mode: "walk", interests: [], now: WED_15 }, ds([bad]));
    expect(r.pick).toBeNull();
    expect(r.counts.unknown_hours).toBe(1);
  });
  it("도보 경로가 없는 곳은 도보 추천에서 빠진다", () => {
    const far = cand("far", { travel: { car: { go: 10, back: 10, m: 6000 } } });
    expect(recommend({ remainingMin: 90, mode: "walk", interests: [], now: WED_15 }, ds([far])).counts.no_route).toBe(1);
  });
  it("차량은 주차 5분을 더한다", () => {
    const r = recommend({ remainingMin: 50, mode: "car", interests: [], now: WED_15 }, ds([cand("a")]));
    expect(r.pick?.go).toBe(9);
    expect(r.pick?.parking).toBe(5);
  });
  it("관심 항목만 남기고, 없으면 전체에서 고른 뒤 표시한다", () => {
    const cafe = cand("cafe");
    const shop = cand("shop", { category: "shopping" });
    const r1 = recommend({ remainingMin: 60, mode: "walk", interests: ["shop"], now: WED_15 }, ds([cafe, shop]));
    expect(r1.pick?.candidate.id).toBe("shop");
    expect(r1.fallbackUsed).toBe(false);
    const r2 = recommend({ remainingMin: 60, mode: "walk", interests: ["culture"], now: WED_15 }, ds([cafe, shop]));
    expect(r2.pick).not.toBeNull();
    expect(r2.fallbackUsed).toBe(true);
  });
  it("체험·문화에 가점을 준다", () => {
    const cafe = cand("cafe");
    const exp = cand("exp", { category: "experience", travel: { walk: { go: 12, back: 12, m: 800 } }, dwell_min: 20 });
    const r = recommend({ remainingMin: 90, mode: "walk", interests: [], now: WED_15 }, ds([cafe, exp]));
    expect(r.pick?.candidate.id).toBe("exp");
  });
  it("결과가 없으면 억지로 추천하지 않는다", () => {
    const r = recommend({ remainingMin: 30, mode: "walk", interests: [], now: at("2026-10-07T23:30") }, ds([cand("a")]));
    expect(r.pick).toBeNull();
    expect(r.alternatives).toEqual([]);
  });
  it("같은 입력이면 같은 결과", () => {
    const list = ["b", "a", "c"].map((id) => cand(id));
    const input = { remainingMin: 60, mode: "walk" as Mode, interests: [] as Interest[], now: WED_15 };
    const r1 = recommend(input, ds(list));
    const r2 = recommend(input, ds([...list].reverse()));
    expect(r1.pick?.candidate.id).toBe("a");
    expect(r2.pick?.candidate.id).toBe(r1.pick?.candidate.id);
    expect(r2.alternatives.map((p) => p.candidate.id)).toEqual(r1.alternatives.map((p) => p.candidate.id));
  });
});

describe("속성: 추천 결과는 절대 남은 시간을 넘지 않는다", () => {
  const sample = JSON.parse(readFileSync(join(__dirname, "../../../public/data/candidates.json"), "utf-8")) as Dataset;
  // 결정적 난수
  let seed = 42;
  const rand = () => ((seed = (seed * 1664525 + 1013904223) % 2 ** 32) / 2 ** 32);
  const interests: Interest[] = ["eat", "shop", "culture"];

  it("무작위 입력 1,000개", () => {
    let recommended = 0;
    for (let i = 0; i < 1000; i++) {
      const T = 20 + Math.floor(rand() * 101);
      const mode: Mode = rand() < 0.5 ? "walk" : "car";
      const now = addMin(at("2026-09-28T00:00"), Math.floor(rand() * 60 * 24 * 60));
      const picked = interests.filter(() => rand() < 0.4);
      const r = recommend({ remainingMin: T, mode, interests: picked, now }, sample);
      for (const p of [r.pick, ...r.alternatives].filter(Boolean)) {
        recommended++;
        expect(p!.go + p!.dwell + p!.back + p!.buffer).toBeLessThanOrEqual(T);
        expect(p!.slack).toBeGreaterThanOrEqual(p!.buffer);
        expect(p!.candidate.hours.parse_status).toBe("ok");
        expect(p!.closesAt!.getTime()).toBeGreaterThanOrEqual(addMin(now, p!.go + p!.dwell).getTime());
      }
    }
    expect(recommended).toBeGreaterThan(100);
  });
});
