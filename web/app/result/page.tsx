import type { Metadata } from "next";
import { Suspense } from "react";
import { ResultView } from "@/components/ResultView";

export const metadata: Metadata = { title: "추천 결과 · 다음 한 곳" };

export default function ResultPage() {
  return (
    <Suspense fallback={<div className="mt-20 h-72 animate-pulse rounded-2xl bg-surface" />}>
      <ResultView />
    </Suspense>
  );
}
