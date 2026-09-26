"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ENGINE } from "@/lib/engine/config";
import type { Interest, Mode } from "@/lib/engine/types";
import { DEMO_TIMES, INTEREST_LABEL, MODE_LABEL } from "@/lib/labels";
import { readQuery, toSearch } from "@/lib/params";
import { DemoTimeBanner } from "./Chrome";

const chip = "rounded-full border px-4 py-2 text-[15px] transition-colors";
const on = "border-accent bg-accent text-on-accent";
const off = "border-line bg-surface text-ink";

export function InputForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const initial = readQuery(new URLSearchParams(sp.toString()));
  const [minutes, setMinutes] = useState(initial.remainingMin);
  const [mode, setMode] = useState<Mode>(initial.mode);
  const [interests, setInterests] = useState<Interest[]>(initial.interests);
  const [at, setAt] = useState<string | null>(initial.at);
  const custom = !(ENGINE.presets as readonly number[]).includes(minutes);

  const toggle = (i: Interest) =>
    setInterests((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]));
  const step = (d: number) =>
    setMinutes((m) => Math.min(ENGINE.maxRemaining, Math.max(ENGINE.minRemaining, m + d)));

  return (
    <form
      className="flex flex-col gap-7"
      onSubmit={(e) => {
        e.preventDefault();
        router.push(`/result?${toSearch({ remainingMin: minutes, mode, interests, at })}`);
      }}
    >
      {at && <DemoTimeBanner at={at} />}

      <section>
        <h2 className="mb-3 text-[15px] font-medium text-muted">남은 시간</h2>
        <div className="grid grid-cols-3 gap-2">
          {ENGINE.presets.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setMinutes(p)}
              aria-pressed={minutes === p}
              className={`rounded-xl border py-4 text-[20px] font-bold ${minutes === p ? on : off}`}
            >
              {p}분
            </button>
          ))}
        </div>
        <div className={`mt-2 flex items-center justify-between rounded-xl border px-3 py-2 ${custom ? "border-accent" : "border-line"} bg-surface`}>
          <span className="text-[14px] text-muted">직접 입력</span>
          <div className="flex items-center gap-3">
            <button type="button" aria-label="5분 줄이기" onClick={() => step(-5)} className="h-9 w-9 rounded-full border border-line text-lg">
              −
            </button>
            <span className="w-16 text-center text-[17px] font-bold tabular-nums">{minutes}분</span>
            <button type="button" aria-label="5분 늘리기" onClick={() => step(5)} className="h-9 w-9 rounded-full border border-line text-lg">
              +
            </button>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-[15px] font-medium text-muted">이동수단</h2>
        <div className="grid grid-cols-2 gap-2">
          {(["walk", "car"] as Mode[]).map((m) => (
            <button key={m} type="button" onClick={() => setMode(m)} aria-pressed={mode === m} className={`rounded-xl border py-3 text-[16px] font-medium ${mode === m ? on : off}`}>
              {MODE_LABEL[m]}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-[15px] font-medium text-muted">
          관심 항목 <span className="text-[13px]">(선택 안 해도 돼요)</span>
        </h2>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(INTEREST_LABEL) as Interest[]).map((i) => (
            <button key={i} type="button" onClick={() => toggle(i)} aria-pressed={interests.includes(i)} className={`${chip} ${interests.includes(i) ? on : off}`}>
              {INTEREST_LABEL[i]}
            </button>
          ))}
        </div>
      </section>

      <button type="submit" className="rounded-2xl bg-accent py-4 text-[18px] font-bold text-on-accent shadow-sm active:scale-[0.99]">
        갈 곳 찾기
      </button>

      <details className="text-[13px] text-muted">
        <summary className="cursor-pointer">다른 시각 기준으로 찾기</summary>
        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" onClick={() => setAt(null)} className={`${chip} text-[13px] ${!at ? on : off}`}>
            지금
          </button>
          {DEMO_TIMES.map((d) => (
            <button key={d.at} type="button" onClick={() => setAt(d.at)} className={`${chip} text-[13px] ${at === d.at ? on : off}`}>
              {d.label}
            </button>
          ))}
        </div>
      </details>
    </form>
  );
}
