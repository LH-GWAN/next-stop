import { Suspense } from "react";
import { Footer } from "@/components/Chrome";
import { InputForm } from "@/components/InputForm";
import { datasetMeta } from "@/lib/data/meta";

export default function Home() {
  const meta = datasetMeta();
  return (
    <>
      <header className="pt-10 pb-6">
        <p className="text-[14px] font-medium text-accent">다음 한 곳 · {meta.originName}</p>
        <h1 className="mt-2 text-[26px] leading-snug font-bold">
          돌아가기까지
          <br />
          얼마나 남았나요?
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">
          지금 문을 열었고, 남은 시간 안에 다녀올 수 있는 곳을 <b className="text-ink">3곳까지</b> 골라드려요.
        </p>
      </header>
      <main className="flex flex-col gap-5 pb-10">
        <Suspense>
          <InputForm />
        </Suspense>
      </main>
      <Footer sample={meta.mode === "sample"} estimatedTravel={meta.travelMode !== "tmap"} />
    </>
  );
}
