import type { Category, Interest } from "./types";

/** 추천 규칙 설정값. 근거는 docs/ENGINE_RULES.md 참고. */
export const ENGINE = {
  /** 여유 시간 = max(minBuffer, ceil(bufferRatio × 남은 시간)) */
  minBuffer: 10,
  bufferRatio: 0.2,
  /** 차량 이동 시 목적지 주차 시간(분) */
  parkingMin: 5,
  weights: {
    /** 관심 항목 일치 */
    interest: 3,
    /** 체험·문화 가점: 데이터랩 양평군 여가서비스업 소비 비중 4.8% */
    leisure: 2,
    /** 이동 시간이 짧을수록 (1 - go / T) */
    shortTrip: 2,
    /** 참가자가 직접 확인한 영업정보 */
    verified: 1,
  },
  presets: [30, 50, 90],
  minRemaining: 20,
  maxRemaining: 120,
} as const;

export const INTEREST_CATEGORIES: Record<Interest, Category[]> = {
  eat: ["cafe", "food"],
  shop: ["shopping"],
  culture: ["experience", "culture", "sight"],
};

export const LEISURE: Category[] = ["experience", "culture"];

export function bufferFor(remainingMin: number): number {
  return Math.max(ENGINE.minBuffer, Math.ceil(ENGINE.bufferRatio * remainingMin));
}
