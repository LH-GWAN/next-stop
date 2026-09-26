"""데이터랩 147개 시군 비교로 실증 지역을 고르는 과정을 재현한다.

출처: 한국관광 데이터랩 > 지역별 분석 > 지역별 관광 현황 (2025.9.~2026.8., 월간 조회)
방문자 수와 소비 금액은 데이터랩 안내에 따라 상대 비교에만 쓴다.

실행: uv run python analysis/select_region.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "raw" / "datalab" / "시군별_관광지표_202509-202608.csv"
IMG_DIR = ROOT.parent / "docs" / "img"
OUT_JSON = ROOT / "out" / "region_selection.json"

SEARCH = "관광목적지검색량_천건"
STAY_RATIO = "숙박방문자비율_퍼센트"
DWELL = "평균체류시간_분"
SPEND = "방문1회당관광소비_외지인_원"
VISITORS = "외지인방문자_연인원_천명"

# 데이터랩 '지역별 관광 현황' 양평군 업종별 관광소비(외지인) 비중. CSV에 없어 조회값을 옮겨 적음.
YANGPYEONG_SPEND_MIX = {
    "식음료업": 40.2,
    "운송업": 28.8,
    "쇼핑업": 23.4,
    "여가서비스업": 4.8,
    "숙박업": 2.2,
    "의료웰니스업": 0.5,
}

# 데이터랩 내비게이션 검색 중 숙박 목적지 비중(%). 4곳 비교용 조회값.
LODGING_SEARCH_SHARE = {"양평군": 14.2, "광명시": 2.9, "양산시": 3.8, "구리시": 3.3}


def load() -> pd.DataFrame:
    return pd.read_csv(CSV, encoding="utf-8-sig", dtype={"시군구코드": str})


def select(df: pd.DataFrame) -> dict:
    n = len(df)
    top_n = n // 3  # 147 → 49곳
    ranked = df.sort_values(SEARCH, ascending=False).reset_index(drop=True)
    cutoff_third = int(ranked.loc[top_n - 1, SEARCH])
    medians = {c: float(df[c].median()) for c in (STAY_RATIO, DWELL, SPEND)}

    in_top = df[SEARCH] >= cutoff_third
    below_median = (
        (df[STAY_RATIO] <= medians[STAY_RATIO])
        & (df[DWELL] <= medians[DWELL])
        & (df[SPEND] <= medians[SPEND])
    )
    selected = df[in_top & below_median].sort_values(SEARCH, ascending=False)

    # 요약 문서의 '164만 7천 건 이상' 컷오프로도 같은 결과인지 확인
    alt_cutoff = 1647
    selected_alt = sorted(df[(df[SEARCH] >= alt_cutoff) & below_median]["시군"].tolist())

    yp = df[df["시군"] == "양평군"].iloc[0]
    ranks = {
        "관광목적지검색량_순위": int(df[SEARCH].rank(ascending=False, method="min")[yp.name]),
        "외지인방문자_순위": int(df[VISITORS].rank(ascending=False, method="min")[yp.name]),
        "평균체류시간_짧은순위": int(df[DWELL].rank(ascending=True, method="min")[yp.name]),
    }
    return {
        "n_regions": n,
        "period": "2025.9.~2026.8.",
        "search_cutoff_top_third_thousand": cutoff_third,
        "search_cutoff_top_third_count": int(in_top.sum()),
        "search_cutoff_summary_doc_thousand": alt_cutoff,
        "search_cutoff_summary_doc_count": int((df[SEARCH] >= alt_cutoff).sum()),
        "selected_alt_cutoff": selected_alt,
        "medians": medians,
        "selected": [
            {
                "시군": r["시군"],
                "시도": r["시도"],
                "관광목적지검색량_천건": int(r[SEARCH]),
                "숙박방문자비율_퍼센트": float(r[STAY_RATIO]),
                "평균체류시간_분": int(r[DWELL]),
                "방문1회당관광소비_외지인_원": int(r[SPEND]),
                "숙박목적지_검색비중_퍼센트": LODGING_SEARCH_SHARE.get(r["시군"]),
            }
            for _, r in selected.iterrows()
        ],
        "final": {
            "시군": "양평군",
            "시군구코드": str(yp["시군구코드"]),
            "reason": "4곳 중 숙박 목적지 검색 비중이 14.2%로 관광 목적 방문이 뚜렷함(나머지 3곳은 3% 안팎의 도시형 생활권)",
            "외지인방문자_연인원_천명": int(yp[VISITORS]),
            "관광목적지검색량_천건": int(yp[SEARCH]),
            "숙박방문자비율_퍼센트": float(yp[STAY_RATIO]),
            "평균체류시간_분": int(yp[DWELL]),
            "방문1회당관광소비_외지인_원": int(yp[SPEND]),
            **ranks,
        },
        "yangpyeong_spend_mix": YANGPYEONG_SPEND_MIX,
        "origin": {"name": "두물머리", "reason": "양평군 외지인 인기관광지 1위, 중심관광지 1위"},
    }


def _korean_font() -> None:
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"):
        if name in installed:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def plot_scatter(df: pd.DataFrame, result: dict, path: Path) -> None:
    _korean_font()
    fig, ax = plt.subplots(figsize=(8, 6), dpi=160)
    top = df[SEARCH] >= result["search_cutoff_top_third_thousand"]
    ax.scatter(df.loc[~top, DWELL], df.loc[~top, SPEND] / 1000, s=14, c="#c9ced6", label="그 외 시군")
    ax.scatter(df.loc[top, DWELL], df.loc[top, SPEND] / 1000, s=22, c="#6b8fd6", label="검색량 상위 3분의 1")
    names = {s["시군"] for s in result["selected"]}
    sel = df[df["시군"].isin(names)]
    ax.scatter(sel[DWELL], sel[SPEND] / 1000, s=60, c="#e4572e", zorder=3, label="4가지 조건 모두 충족")
    offsets = {"양평군": (10, 14), "구리시": (-8, -20), "광명시": (4, -18), "양산시": (10, 6)}
    for _, r in sel.iterrows():
        ax.annotate(r["시군"], (r[DWELL], r[SPEND] / 1000), xytext=offsets.get(r["시군"], (6, 4)),
                    textcoords="offset points", fontsize=10, fontweight="bold",
                    arrowprops={"arrowstyle": "-", "color": "#999", "lw": 0.6})
    m = result["medians"]
    ax.axvline(m[DWELL], color="#888", lw=0.8, ls="--")
    ax.axhline(m[SPEND] / 1000, color="#888", lw=0.8, ls="--")
    ax.set_xlabel("외지인 평균 체류시간(분)")
    ax.set_ylabel("방문 1회당 관광소비(천 원, 상대 비교)")
    ax.set_title("147개 시군: 짧게 머물고 적게 쓰는 관광 수요 지역")
    ax.set_ylim(0, df[SPEND].quantile(0.97) / 1000)
    ax.set_xlim(df[DWELL].min() - 50, df[DWELL].quantile(0.99) + 50)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.text(0.01, -0.12, "출처: 한국관광 데이터랩 지역별 관광 현황(2025.9.~2026.8.). 점선은 중앙값. 일부 이상치는 축 밖.",
            transform=ax.transAxes, fontsize=8, color="#666")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_spend_mix(path: Path) -> None:
    _korean_font()
    items = sorted(YANGPYEONG_SPEND_MIX.items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=160)
    colors = ["#e4572e" if k == "여가서비스업" else "#9aa7bd" for k, _ in items]
    ax.barh([k for k, _ in items], [v for _, v in items], color=colors)
    for i, (_, v) in enumerate(items):
        ax.text(v + 0.6, i, f"{v}%", va="center", fontsize=9)
    ax.set_xlim(0, 48)
    ax.set_xlabel("외지인 관광소비 비중(%)")
    ax.set_title("양평군 업종별 관광소비: 체험·문화(여가서비스업) 4.8%")
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(0.0, -0.3, "출처: 한국관광 데이터랩 지역별 관광 현황, 신용카드 관광소비(2025.9.~2026.8.)",
            transform=ax.transAxes, fontsize=8, color="#666")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    df = load()
    result = select(df)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    plot_scatter(df, result, IMG_DIR / "region_scatter.png")
    plot_spend_mix(IMG_DIR / "yangpyeong_spend_mix.png")
    for path in (OUT_JSON,):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"대상 시군: {result['n_regions']}곳")
    print(f"검색량 상위 3분의 1 컷오프: {result['search_cutoff_top_third_thousand']:,}천 건 "
          f"({result['search_cutoff_top_third_count']}곳)")
    print(f"요약 문서 컷오프 {result['search_cutoff_summary_doc_thousand']:,}천 건 적용 시: "
          f"{result['search_cutoff_summary_doc_count']}곳, 선정 결과 {result['selected_alt_cutoff']}")
    print("중앙값:", {k: v for k, v in result["medians"].items()})
    print("4가지 조건 충족:", [s["시군"] for s in result["selected"]])
    f = result["final"]
    print(f"최종 선정: {f['시군']} / 검색량 {f['관광목적지검색량_순위']}위, 방문자 {f['외지인방문자_순위']}위, "
          f"체류시간 짧은 순 {f['평균체류시간_짧은순위']}위")


if __name__ == "__main__":
    main()
