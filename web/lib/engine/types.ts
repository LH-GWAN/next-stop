export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";
export type Category = "cafe" | "food" | "shopping" | "experience" | "culture" | "sight";
export type Mode = "walk" | "car";
export type Interest = "eat" | "shop" | "culture";

export interface Period {
  months: number[];
  /** 요일별 영업 구간 ["HH:MM", "HH:MM"]. 24:00을 넘으면 익일 새벽. null이면 정보 없음. hol은 공휴일 시간. */
  weekly: Partial<Record<Weekday | "hol", [string, string][] | null>>;
}

export interface Hours {
  periods: Period[];
  last_entry: string | null;
  last_entry_before_close_min: number | null;
  closed: {
    weekdays: Weekday[];
    holiday_shift: boolean;
    holidays: string[];
    dates: string[];
    monthly: { nth: number; weekday: Weekday }[];
  };
  parse_status: "ok" | "partial" | "fail";
  issues: string[];
  raw_usetime: string;
  raw_restdate: string;
  source: "tourapi" | "verified" | "sample";
  verified_on: string | null;
}

export interface Leg {
  go: number;
  back: number;
  m: number;
}

export interface Candidate {
  id: string;
  name: string;
  category: Category;
  content_type_id: number;
  lat: number;
  lng: number;
  addr: string;
  tel: string;
  hours: Hours;
  dwell_min: number;
  dwell_source: string;
  travel: Partial<Record<Mode, Leg>>;
  travel_source: "tmap" | "estimate";
  attribution: string;
}

export interface HolidayInfo {
  name: string;
  kinds: string[];
}

export interface Dataset {
  mode: "sample" | "live";
  /** 이동시간 출처: TMAP 경로 결과, 직선거리 추정값, 또는 둘이 섞임 */
  travel_mode?: "tmap" | "estimate" | "mixed";
  generated_at: string;
  origin: { id: string; name: string; lat: number; lng: number; addr: string };
  candidates: Candidate[];
  holidays: Record<string, HolidayInfo>;
}

export interface RecommendInput {
  remainingMin: number;
  mode: Mode;
  interests: Interest[];
  now: Date;
}

export type Verdict = "ok" | "too_long" | "closed" | "unknown_hours" | "no_route";

export interface Plan {
  candidate: Candidate;
  go: number;
  dwell: number;
  back: number;
  parking: number;
  buffer: number;
  /** 필요한 총 시간(여유 포함) */
  total: number;
  /** 남은 시간 - (이동 + 이용 + 복귀 + 주차). 항상 buffer 이상이다. */
  slack: number;
  closesAt: Date | null;
  score: number;
  reasons: string[];
}

export interface Recommendation {
  pick: Plan | null;
  alternatives: Plan[];
  fallbackUsed: boolean;
  buffer: number;
  counts: Record<Verdict, number> & { total: number };
  /** 결과가 없을 때: 시간을 늘리면 가능한 가장 가까운 곳 */
  nearMiss: { candidate: Candidate; neededMin: number } | null;
}
