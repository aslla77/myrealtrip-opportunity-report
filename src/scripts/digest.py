"""
digest.py — 분석 산출을 하나의 '데이터 다이제스트'로 정리(사실·숫자·표만).
!!! 여기서는 보고서 '문장'을 쓰지 않는다. Codex(LLM)가 이 다이제스트+그림을 읽고 보고서를 직접 쓴다.
출력: out/data_digest.md (전체 표·핵심 수치·그림 목록·근거 등급) — Codex의 입력.
"""
import os, datetime
import pandas as pd

OUT = "out"
def load(name):
    p = os.path.join(OUT, name)
    return pd.read_csv(p) if os.path.exists(p) else None
def f(v, s=""):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:g}{s}"

def main():
    cd, opp = load("country_destinations.csv"), load("opportunity_mk2.csv")
    leaders = load("leaders_all_destinations.csv")
    L = []
    L.append("# DATA DIGEST — mk2 (사실·숫자만 · 보고서는 Codex가 이걸 읽고 작성)")
    L.append(f"- 생성 {datetime.date.today().isoformat()} · 패널 최근 12개월 기준 · 수치=공개통계 코드 재계산")
    L.append("- 등급: 입국통계·좌표=A / 직항시간=B·C(라벨)")
    L.append("- 그림: `figs/country_travel_heatmap.png`(국가별 여행지 히트맵), `figs/opportunity_map.png`(거리-보정 기회맵)")
    L.append("")

    if cd is not None:
        L.append("## [DATA] 국가별 많이 가는 여행지 (패널 내 점유율 %)")
        focus = ["South Korea","Indonesia","Thailand","Japan","Taiwan","China","USA","Malaysia",
                 "Vietnam","Philippines","Australia","NewZealand","Canada","Singapore","Macao"]
        L.append("| 출발국 | 1위 | 2위 | 3위 | 4위 | 5위 |")
        L.append("|---|---|---|---|---|---|")
        for c in focus:
            t = cd[(cd.source_country == c) & (cd.dest_rank <= 5)].sort_values("dest_rank")
            if not len(t): continue
            cells = [f"{r.dest} {f(r.panel_share,'%')}" for _, r in t.iterrows()] + ["—"]*5
            L.append(f"| {c} | " + " | ".join(cells[:5]) + " |")
        L.append(f"- 전체 출발국 {cd.source_country.nunique()}개 (전체 raw: `out/country_destinations.csv`)")
        L.append("")

    if opp is not None:
        L.append("## [DATA] 목적지 기회 랭킹 (리드국이 가는 곳 · 거리-보정)")
        L.append("| 목적지 | 관문 | 시간h | 거리km | 리드국(수) | 리드국모멘텀% | 한국YoY% | 한국점유율%(순위) | 카테고리 | 점수 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in opp.sort_values("opp_score", ascending=False).iterrows():
            L.append(f"| {r.dest} | {r.gateway} | {f(r.hours)} | {f(round(r.dist_km))} | {r.best_leader}({int(r.n_leaders)}) "
                     f"| {f(r.leader_yoy,'%')} | {f(r.kr_yoy,'%')} | {f(r.kr_share,'%')}(#{int(r.kr_rank)}) | {r.category} | {f(r.opp_score)} |")
        L.append("- 카테고리: 기회후보(점유율<3%·저침투) / 성숙·포화(≥8%·제외) / 중립. 점수=리드국모멘텀×저침투×거리가중.")
        L.append("")

    if leaders is not None and "went_first" in leaders.columns:
        wf = leaders[leaders.went_first == True].sort_values("corr", ascending=False)
        L.append("## [DATA] 통계 검증된 선행쌍 (리드국이 한국을 앞선 목적지 · z≥3)")
        L.append("| 목적지 | 리드국 | 선행(개월) | 닮음corr | 우연아님z |")
        L.append("|---|---|---|---|---|")
        for _, r in wf.head(20).iterrows():
            L.append(f"| {r.dest} | {r.country} | +{int(r.lead_months)} | {f(r.corr)} | {f(r.z)} |")
        L.append("- 참고: 두 목적지 이상에서 일관 선행한 나라는 없음(동조화가 기본). 선행=보조 근거.")
        L.append("")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "data_digest.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("[digest] out/data_digest.md 생성 — Codex가 이 데이터를 읽고 보고서를 작성한다.")

if __name__ == "__main__":
    main()
