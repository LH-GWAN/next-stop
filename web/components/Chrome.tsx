import { formatKstDateTime, parseKstLocal } from "@/lib/engine/time";

export function DemoTimeBanner({ at }: { at: string }) {
  const t = parseKstLocal(at);
  if (!t) return null;
  return (
    <div className="rounded-lg bg-accent-soft px-3 py-2 text-[13px] text-accent">
      <b>{formatKstDateTime(t)}</b> 기준으로 찾아요.
    </div>
  );
}

export function Footer({ sample, estimatedTravel }: { sample?: boolean; estimatedTravel?: boolean }) {
  return (
    <footer className="mt-auto border-t border-line pt-4 pb-8 text-[12px] leading-relaxed text-muted">
      {sample ? (
        <p>API 키가 필요합니다. 지금은 샘플 장소로 동작합니다.</p>
      ) : estimatedTravel ? (
        <>
          <p>장소·영업 정보: 한국관광공사 TourAPI</p>
          <p className="mt-1">이동시간은 직선거리로 추정한 값이에요. 실제 경로 계산은 TMAP API 키가 필요합니다.</p>
        </>
      ) : (
        <p>장소·영업 정보: 한국관광공사 TourAPI · 이동시간: TMAP</p>
      )}
      <p className="mt-1">영업정보는 바뀔 수 있어요. 방문 전 한 번 더 확인해 주세요.</p>
    </footer>
  );
}
