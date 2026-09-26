import { atKst, hhmmToMin, kstDay, kstEpochDay, type KstDay } from "./time";
import type { HolidayInfo, Hours } from "./types";

type Holidays = Record<string, HolidayInfo>;

function isPublicHoliday(day: KstDay, holidays: Holidays): boolean {
  return Boolean(holidays[day.iso]?.kinds.includes("public"));
}

function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/** 그날이 쉬는 날인지. 영업시간 텍스트가 아니라 closed 규칙만 본다. */
export function isClosedDay(hours: Hours, day: KstDay, holidays: Holidays): boolean {
  const c = hours.closed;
  const holidayToday = isPublicHoliday(day, holidays);

  if (c.weekdays.includes(day.weekday)) {
    // "공휴일인 경우 다음 날 휴무": 휴무 요일이 공휴일이면 그날은 연다
    if (!(c.holiday_shift && holidayToday)) return true;
  }
  if (c.holiday_shift) {
    const prev = kstDay(day.epochDay - 1);
    if (c.weekdays.includes(prev.weekday) && isPublicHoliday(prev, holidays)) return true;
  }
  const kinds = holidays[day.iso]?.kinds ?? [];
  if (c.holidays.some((h) => kinds.includes(h))) return true;
  if (c.dates.includes(day.iso.slice(5))) return true;
  for (const rule of c.monthly) {
    if (rule.weekday !== day.weekday) continue;
    const nth = Math.ceil(day.day / 7);
    const isLast = day.day + 7 > daysInMonth(day.year, day.month);
    if (rule.nth === nth || (rule.nth === -1 && isLast)) return true;
  }
  return false;
}

/** 그날(서비스 날짜 기준)의 영업 구간. 정보가 없으면 null. */
export function intervalsFor(hours: Hours, day: KstDay, holidays: Holidays): [number, number][] | null {
  const period = hours.periods.find((p) => p.months.includes(day.month));
  if (!period) return null;
  const useHol = isPublicHoliday(day, holidays) && period.weekly.hol;
  const ranges = useHol ? period.weekly.hol : period.weekly[day.weekday];
  if (!ranges) return null;
  return ranges.map(([s, e]) => [hhmmToMin(s), hhmmToMin(e)]);
}

export interface OpenCheck {
  open: boolean;
  closesAt: Date | null;
  reason: "open" | "closed_day" | "outside_hours" | "after_last_entry" | "unknown";
}

/**
 * 도착 시각에 열려 있고, 떠나는 시각까지 영업이 이어지는지.
 * 전날 밤부터 이어지는 심야 영업(예: 17:00~26:00)도 본다.
 */
export function checkOpen(hours: Hours, arrival: Date, departure: Date, holidays: Holidays): OpenCheck {
  if (hours.parse_status !== "ok") return { open: false, closesAt: null, reason: "unknown" };
  const today = kstEpochDay(arrival);
  let sawClosedDay = false;
  let sawUnknown = false;

  for (const serviceDay of [today, today - 1]) {
    const day = kstDay(serviceDay);
    if (isClosedDay(hours, day, holidays)) {
      if (serviceDay === today) sawClosedDay = true;
      continue;
    }
    const ranges = intervalsFor(hours, day, holidays);
    if (!ranges) {
      if (serviceDay === today) sawUnknown = true;
      continue;
    }
    for (const [s, e] of ranges) {
      const start = atKst(serviceDay, s);
      const end = atKst(serviceDay, e);
      if (arrival < start || arrival >= end) continue;
      if (departure > end) return { open: false, closesAt: end, reason: "outside_hours" };
      let lastEntry: Date | null = null;
      if (hours.last_entry) {
        let le = hhmmToMin(hours.last_entry);
        if (le < s) le += 24 * 60;
        lastEntry = atKst(serviceDay, le);
      } else if (hours.last_entry_before_close_min != null) {
        lastEntry = new Date(end.getTime() - hours.last_entry_before_close_min * 60_000);
      }
      if (lastEntry && arrival > lastEntry) return { open: false, closesAt: end, reason: "after_last_entry" };
      return { open: true, closesAt: end, reason: "open" };
    }
  }
  if (sawUnknown) return { open: false, closesAt: null, reason: "unknown" };
  return { open: false, closesAt: null, reason: sawClosedDay ? "closed_day" : "outside_hours" };
}
