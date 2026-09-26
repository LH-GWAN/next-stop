import { ENGINE } from "./engine/config";
import { parseKstLocal } from "./engine/time";
import type { Interest, Mode } from "./engine/types";

export interface Query {
  remainingMin: number;
  mode: Mode;
  interests: Interest[];
  /** 시연 모드 시각 문자열(KST). 없으면 현재 시각 */
  at: string | null;
}

const INTERESTS: Interest[] = ["eat", "shop", "culture"];

export function readQuery(sp: URLSearchParams): Query {
  const t = Number(sp.get("t"));
  const remainingMin = Number.isFinite(t) && t > 0
    ? Math.min(ENGINE.maxRemaining, Math.max(ENGINE.minRemaining, Math.round(t)))
    : 50;
  const mode: Mode = sp.get("mode") === "car" ? "car" : "walk";
  const interests = (sp.get("i") ?? "").split(",").filter((x): x is Interest => INTERESTS.includes(x as Interest));
  const at = sp.get("at");
  return { remainingMin, mode, interests, at: parseKstLocal(at) ? at : null };
}

export function toSearch(q: Partial<Query>): string {
  const sp = new URLSearchParams();
  if (q.remainingMin) sp.set("t", String(q.remainingMin));
  if (q.mode) sp.set("mode", q.mode);
  if (q.interests?.length) sp.set("i", q.interests.join(","));
  if (q.at) sp.set("at", q.at);
  return sp.toString();
}
