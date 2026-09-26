"use client";

import { useEffect, useState } from "react";
import type { Dataset } from "../engine/types";

let cache: Promise<Dataset> | null = null;

function load(): Promise<Dataset> {
  cache ??= fetch("/data/candidates.json").then((r) => {
    if (!r.ok) throw new Error(`후보 데이터를 불러오지 못했습니다 (${r.status})`);
    return r.json() as Promise<Dataset>;
  });
  return cache;
}

export function useDataset(): { data: Dataset | null; error: string | null } {
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    load().then(setData, (e: Error) => setError(e.message));
  }, []);
  return { data, error };
}
