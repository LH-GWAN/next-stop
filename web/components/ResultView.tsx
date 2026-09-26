"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useDataset } from "@/lib/data/useDataset";
import { recommend } from "@/lib/engine/recommend";
import { parseKstLocal } from "@/lib/engine/time";
import { INTEREST_LABEL, MODE_LABEL } from "@/lib/labels";
import { readQuery, toSearch } from "@/lib/params";
import { DemoTimeBanner, Footer } from "./Chrome";
import { PlanCard } from "./PlanCard";

const REPORT_URL = process.env.NEXT_PUBLIC_REPORT_URL;

export function ResultView() {
  const sp = useSearchParams();
  const q = readQuery(new URLSearchParams(sp.toString()));
  const { data, error } = useDataset();
  // '지금'은 화면을 연 시각으로 고정한다(다시 그려도 결과가 바뀌지 않게)
  const [openedAt] = useState(() => new Date());
  const now = q.at ? parseKstLocal(q.at)! : openedAt;

  const result = data ? recommend({ remainingMin: q.remainingMin, mode: q.mode, interests: q.interests, now }, data) : null;

  const summary = [`${q.remainingMin}분`, MODE_LABEL[q.mode], ...q.interests.map((i) => INTEREST_LABEL[i])].join(" · ");
  const back = `/?${toSearch(q)}`;
  const sample = data?.mode === "sample";

  return (
    <>
      <header className="flex items-center justify-between pt-6 pb-4">
        <Link href={back} className="text-[15px] text-muted">
          ← 다시 입력
        </Link>
        <span className="rounded-full border border-line bg-surface px-3 py-1 text-[13px]">{summary}</span>
      </header>

      <main className="flex flex-col gap-4 pb-10">
        {q.at && <DemoTimeBanner at={q.at} />}
        {error && <p className="text-bad">{error}</p>}
        {!data && !error && <div className="h-72 animate-pulse rounded-2xl bg-surface" />}

        {data && result && (
          <>
            {result.pick ? (
              <>
                {result.fallbackUsed && (
                  <p className="rounded-lg bg-warn-soft px-3 py-2 text-[13px] text-warn">
                    선택한 항목 중에는 지금 갈 수 있는 곳이 없어 다른 곳을 추천했어요.
                  </p>
                )}
                <div className="flex flex-col gap-3">
                  {[result.pick, ...result.alternatives].map((p, i) => (
                    <PlanCard key={p.candidate.id} plan={p} rank={i + 1} mode={q.mode} remainingMin={q.remainingMin} originName={data.origin.name} sample={sample} />
                  ))}
                </div>
              </>
            ) : (
              <section className="rounded-2xl border border-line bg-surface p-5">
                <h2 className="text-[19px] font-bold">지금 남은 시간 안에 다녀올 수 있는 곳을 찾지 못했어요</h2>
                <p className="mt-2 text-[14px] leading-relaxed text-muted">
                  영업 중이면서 이동·이용·복귀·여유 시간이 {q.remainingMin}분 안에 들어오는 곳이 없어요. 억지로 추천하지 않을게요.
                </p>
                {result.nearMiss && result.nearMiss.neededMin <= 120 && (
                  <Link
                    href={`/result?${toSearch({ ...q, remainingMin: result.nearMiss.neededMin })}`}
                    className="mt-4 block rounded-xl bg-accent-soft px-4 py-3 text-[15px] text-accent"
                  >
                    {result.nearMiss.neededMin}분이면 <b>{result.nearMiss.candidate.name}</b>에 다녀올 수 있어요 →
                  </Link>
                )}
              </section>
            )}

            {result.pick && (
              <p className="text-center text-[13px] text-muted">지금 갈 수 있는 {result.counts.ok}곳 중 {1 + result.alternatives.length}곳을 골랐어요</p>
            )}

            {REPORT_URL && (
              <a href={REPORT_URL} target="_blank" rel="noopener noreferrer" className="text-center text-[14px] text-muted underline underline-offset-2">
                정보가 틀려요
              </a>
            )}
          </>
        )}
      </main>
      <Footer sample={sample} estimatedTravel={data ? (data.travel_mode ?? "estimate") !== "tmap" : false} />
    </>
  );
}
