import { ENGINE, INTEREST_CATEGORIES, LEISURE, bufferFor } from "./config";
import { checkOpen } from "./hours";
import { addMin } from "./time";
import type { Candidate, Dataset, Plan, RecommendInput, Recommendation, Verdict } from "./types";

interface Evaluated {
  verdict: Verdict;
  plan?: Plan;
  /** 영업 조건은 맞지만 시간이 모자란 경우 필요한 남은 시간 */
  neededMin?: number;
}

export function evaluate(c: Candidate, input: RecommendInput, data: Dataset): Evaluated {
  const T = input.remainingMin;
  const buffer = bufferFor(T);
  if (c.hours.parse_status !== "ok") return { verdict: "unknown_hours" };
  const leg = c.travel[input.mode];
  if (!leg) return { verdict: "no_route" };

  const parking = input.mode === "car" ? ENGINE.parkingMin : 0;
  const go = leg.go + parking;
  const dwell = c.dwell_min;
  const back = leg.back;
  const total = go + dwell + back + buffer;

  const arrival = addMin(input.now, go);
  const departure = addMin(arrival, dwell);
  const open = checkOpen(c.hours, arrival, departure, data.holidays);
  if (!open.open) return { verdict: open.reason === "unknown" ? "unknown_hours" : "closed" };
  if (total > T) {
    // 시간을 늘리면 가능한지: 여유 규칙을 다시 적용해 필요한 최소 T를 찾는다
    let need = T + 1;
    while (need <= ENGINE.maxRemaining * 2 && go + dwell + back + bufferFor(need) > need) need++;
    return { verdict: "too_long", neededMin: need };
  }

  const plan: Plan = {
    candidate: c,
    go,
    dwell,
    back,
    parking,
    buffer,
    total,
    slack: T - (go + dwell + back),
    closesAt: open.closesAt,
    score: 0,
    reasons: [],
  };
  return { verdict: "ok", plan };
}

function score(plan: Plan, input: RecommendInput): Plan {
  const w = ENGINE.weights;
  const c = plan.candidate;
  const reasons: string[] = [];
  let s = 0;
  const wanted = input.interests.flatMap((i) => INTEREST_CATEGORIES[i]);
  if (wanted.includes(c.category)) {
    s += w.interest;
    reasons.push("관심 항목과 일치");
  }
  if (LEISURE.includes(c.category)) {
    s += w.leisure;
    reasons.push("체험·문화 공간");
  }
  const trip = plan.go - plan.parking;
  s += w.shortTrip * (1 - trip / input.remainingMin);
  if (trip <= 10) reasons.push("가까운 곳");
  if (c.hours.source === "verified") {
    s += w.verified;
    reasons.push("영업시간 확인됨");
  }
  return { ...plan, score: Math.round(s * 1000) / 1000, reasons };
}

export function recommend(input: RecommendInput, data: Dataset): Recommendation {
  const counts = { ok: 0, too_long: 0, closed: 0, unknown_hours: 0, no_route: 0, total: data.candidates.length };
  const feasible: Plan[] = [];
  let nearMiss: Recommendation["nearMiss"] = null;

  for (const c of data.candidates) {
    const e = evaluate(c, input, data);
    counts[e.verdict] += 1;
    if (e.plan) feasible.push(e.plan);
    if (e.verdict === "too_long" && e.neededMin && (!nearMiss || e.neededMin < nearMiss.neededMin)) {
      nearMiss = { candidate: c, neededMin: e.neededMin };
    }
  }

  const wanted = input.interests.flatMap((i) => INTEREST_CATEGORIES[i]);
  let pool = wanted.length ? feasible.filter((p) => wanted.includes(p.candidate.category)) : feasible;
  const fallbackUsed = wanted.length > 0 && pool.length === 0 && feasible.length > 0;
  if (fallbackUsed) pool = feasible;

  const ranked = pool
    .map((p) => score(p, input))
    .sort((a, b) => b.score - a.score || a.candidate.id.localeCompare(b.candidate.id));

  return {
    pick: ranked[0] ?? null,
    alternatives: ranked.slice(1, 3),
    fallbackUsed,
    buffer: bufferFor(input.remainingMin),
    counts,
    nearMiss: ranked.length ? null : nearMiss,
  };
}
