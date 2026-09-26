import type { Weekday } from "./types";

/** 한국은 서머타임이 없으므로 UTC+9 고정으로 계산한다. */
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;
const WEEKDAYS: Weekday[] = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

/** KST 달력 날짜 하나. epochDay는 KST 기준 1970-01-01부터 센 날 수. */
export interface KstDay {
  epochDay: number;
  year: number;
  month: number;
  day: number;
  weekday: Weekday;
  iso: string;
}

export function kstDay(epochDay: number): KstDay {
  const d = new Date(epochDay * DAY_MS);
  const year = d.getUTCFullYear();
  const month = d.getUTCMonth() + 1;
  const day = d.getUTCDate();
  return {
    epochDay,
    year,
    month,
    day,
    weekday: WEEKDAYS[d.getUTCDay()],
    iso: `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
  };
}

export function kstEpochDay(t: Date): number {
  return Math.floor((t.getTime() + KST_OFFSET_MS) / DAY_MS);
}

/** KST 날짜의 자정 + minutes 분에 해당하는 실제 시각 */
export function atKst(epochDay: number, minutes: number): Date {
  return new Date(epochDay * DAY_MS - KST_OFFSET_MS + minutes * 60_000);
}

export function addMin(t: Date, minutes: number): Date {
  return new Date(t.getTime() + minutes * 60_000);
}

export function hhmmToMin(s: string): number {
  const [h, m] = s.split(":").map(Number);
  return h * 60 + m;
}

/** "2026-10-10T15:00" 같은 입력을 KST 시각으로 해석한다. 형식이 틀리면 null. */
export function parseKstLocal(s: string | null | undefined): Date | null {
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})$/.exec(s.trim());
  if (!m) return null;
  const [, y, mo, d, h, mi] = m.map(Number);
  const epochDay = Math.floor(Date.UTC(y, mo - 1, d) / DAY_MS);
  return atKst(epochDay, h * 60 + mi);
}

export function formatKstTime(t: Date): string {
  const ms = t.getTime() + KST_OFFSET_MS;
  const d = new Date(ms);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

export function formatKstDateTime(t: Date): string {
  const day = kstDay(kstEpochDay(t));
  const ko: Record<Weekday, string> = { mon: "월", tue: "화", wed: "수", thu: "목", fri: "금", sat: "토", sun: "일" };
  return `${day.month}월 ${day.day}일(${ko[day.weekday]}) ${formatKstTime(t)}`;
}
