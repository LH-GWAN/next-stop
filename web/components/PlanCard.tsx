import { formatKstTime } from "@/lib/engine/time";
import type { Mode, Plan } from "@/lib/engine/types";
import { CATEGORY_LABEL, MODE_LABEL } from "@/lib/labels";

export function TimeBar({ plan, total }: { plan: Plan; total: number }) {
  const parts = [
    { key: "go", min: plan.go, cls: "bg-go", label: "이동" },
    { key: "stay", min: plan.dwell, cls: "bg-stay", label: "이용" },
    { key: "back", min: plan.back, cls: "bg-back", label: "복귀" },
    { key: "slack", min: plan.slack, cls: "bg-slack", label: "여유" },
  ];
  return (
    <div>
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-full" role="img" aria-label={parts.map((p) => `${p.label} ${p.min}분`).join(", ")}>
        {parts.map((p) => (
          <div key={p.key} className={p.cls} style={{ width: `${(p.min / total) * 100}%` }} />
        ))}
      </div>
      <div className="mt-2 grid grid-cols-4 text-center text-[12px] text-muted">
        {parts.map((p) => (
          <div key={p.key}>
            <span className={`mr-1 inline-block h-2 w-2 rounded-full align-middle ${p.cls}`} />
            {p.label} <b className="text-ink tabular-nums">{p.min}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PlanCard({
  plan,
  mode,
  remainingMin,
  originName,
  sample,
  rank,
}: {
  plan: Plan;
  mode: Mode;
  remainingMin: number;
  originName: string;
  sample: boolean;
  rank: number;
}) {
  const primary = rank === 1;
  const c = plan.candidate;
  const dwellIsDefault = c.dwell_source.startsWith("default");
  const travelIsEstimate = c.travel_source === "estimate";
  const approx = travelIsEstimate ? "약 " : "";
  const travelMin = plan.go - plan.parking;
  const mapUrl = `https://map.kakao.com/link/to/${encodeURIComponent(c.name)},${c.lat},${c.lng}`;

  return (
    <article className={`rounded-2xl border bg-surface p-5 ${primary ? "border-accent/40 shadow-sm" : "border-line"}`}>
      <div className="flex items-center gap-2 text-[14px] font-medium">
        <span className={`rounded-full px-2 py-0.5 text-[12px] font-bold ${primary ? "bg-accent text-on-accent" : "bg-accent-soft text-accent"}`}>
          {primary ? "1 추천" : rank}
        </span>
        <span className="text-stay">지금 영업 중</span>
        {plan.closesAt && <span className="text-muted">· {formatKstTime(plan.closesAt)}까지</span>}
      </div>

      <h2 className={`mt-2 font-bold ${primary ? "text-[24px]" : "text-[20px]"}`}>{c.name}</h2>
      <p className="mt-0.5 text-[14px] text-muted">
        {CATEGORY_LABEL[c.category]} · {MODE_LABEL[mode]} {approx}{travelMin}분{c.travel[mode]?.m ? ` (${(c.travel[mode]!.m / 1000).toFixed(1)}km)` : ""}
      </p>

      <p className="mt-4 text-[15px] leading-relaxed">
        {MODE_LABEL[mode]} {approx}{travelMin}분{plan.parking ? ` + 주차 ${plan.parking}분` : ""} → 이용 {dwellIsDefault ? "약 " : ""}
        {plan.dwell}분 → 복귀 {approx}{plan.back}분.
        <br />
        {originName}에 돌아와도 <b>약 {plan.slack}분 여유</b>가 있어요.
      </p>

      <div className="mt-4">
        <TimeBar plan={plan} total={remainingMin} />
      </div>

      {(dwellIsDefault || (travelIsEstimate && !sample)) && (
        <p className="mt-3 text-[12px] text-muted">
          {[travelIsEstimate && !sample ? "이동 시간은 직선거리로 추정했어요." : "", dwellIsDefault ? "이용 시간은 평균적인 값이에요." : ""]
            .filter(Boolean)
            .join(" ")}
        </p>
      )}

      {plan.reasons.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {plan.reasons.map((r) => (
            <li key={r} className="rounded-full bg-accent-soft px-2.5 py-1 text-[12px] text-accent">
              {r}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5 flex flex-col gap-2">
          {c.addr && <p className="text-[13px] text-muted">{c.addr}</p>}
          {sample ? (
            <span className="rounded-xl border border-line py-3 text-center text-[14px] text-muted">길찾기 (API 키 연결 후 사용)</span>
          ) : (
            <a href={mapUrl} target="_blank" rel="noopener noreferrer" className={`rounded-xl py-3 text-center text-[16px] font-bold ${primary ? "bg-accent text-on-accent" : "border border-accent text-accent"}`}>
              길찾기
            </a>
          )}
      </div>

      <p className="mt-4 text-[11px] text-muted">
        출처: {c.attribution}
        {c.hours.source === "verified" && c.hours.verified_on ? ` · 영업정보 직접 확인 ${c.hours.verified_on}` : ""}
      </p>
    </article>
  );
}
