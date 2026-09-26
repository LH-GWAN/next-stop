import type { Category, Interest, Mode } from "./engine/types";

export const CATEGORY_LABEL: Record<Category, string> = {
  cafe: "카페",
  food: "음식점",
  shopping: "쇼핑",
  experience: "체험",
  culture: "문화시설",
  sight: "관광지",
};

export const INTEREST_LABEL: Record<Interest, string> = {
  eat: "먹거리·카페",
  shop: "쇼핑",
  culture: "체험·문화",
};

export const MODE_LABEL: Record<Mode, string> = { walk: "도보", car: "차량" };

/** 시연용 시각 프리셋 (KST). 2026-10-07 수요일, 2026-10-10 토요일, 둘 다 공휴일 아님 */
export const DEMO_TIMES = [
  { label: "평일 11:00", at: "2026-10-07T11:00" },
  { label: "토요일 15:00", at: "2026-10-10T15:00" },
  { label: "평일 20:00", at: "2026-10-07T20:00" },
];
