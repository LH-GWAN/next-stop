import "server-only";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Dataset } from "../engine/types";

/** 서버에서 빌드 시점에 데이터 모드(sample/live)와 요약만 읽는다. */
export function datasetMeta(): {
  mode: Dataset["mode"];
  travelMode: NonNullable<Dataset["travel_mode"]>;
  generatedAt: string;
  originName: string;
  count: number;
} {
  const d = JSON.parse(readFileSync(join(process.cwd(), "public/data/candidates.json"), "utf-8")) as Dataset;
  return {
    mode: d.mode,
    travelMode: d.travel_mode ?? "estimate",
    generatedAt: d.generated_at,
    originName: d.origin.name,
    count: d.candidates.length,
  };
}

