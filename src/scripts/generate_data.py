"""
generate_data.py — mk2 플러그인 '데이터 생성기'(결정론적 분석 파이프라인).
원천 입력(data/*_arrivals_long.csv)에서 분석·그림·데이터 다이제스트를 처음부터 만든다.
!!! 이 스크립트는 '보고서 문장'을 쓰지 않는다 — 데이터만 만든다.
    보고서는 Codex(LLM)가 out/data_digest.md + 그림을 읽고 직접 작성한다(SKILL.md 참조).

파이프라인:
  0) collect_arrivals.py    → data/*_arrivals_long.csv         (신선도 확인·뒤처지면 수집·선택)
  1) leadlag.py             → out/leaders_all_destinations.csv (YoY 양방향 선행 + 순열검정)
  2) gate.py                → out/stage3_candidates.csv        (리드국 모멘텀 × 한국 침투)
  3) distance.py            → out/opportunity_mk2.csv, out/figs/opportunity_map (거리-보정 기회맵)
  4) country_destinations.py→ out/country_destinations.csv,   out/figs/country_travel_heatmap (국가별 여행지)
  5) digest.py              → out/data_digest.md              (Codex가 읽을 데이터 다이제스트)

사용: python scripts/generate_data.py   (어느 cwd에서 실행하든 플러그인 루트 기준으로 동작)
"""
import os, sys, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 플러그인 루트
STAGES = [
    # (스크립트, 설명, 선택여부) — 선택 단계는 실패해도 파이프라인 계속
    ("collect_arrivals.py",     "입국통계 신선도 확인·수집(뒤처지면)", True),
    ("leadlag.py",              "선행지표 탐지(YoY·순열검정)",        False),
    ("gate.py",                 "침투 게이트·리드국 후보",            False),
    ("distance.py",             "거리-보정 기회맵(opportunity_map)",             False),
    ("country_destinations.py", "국가별 여행지(country_travel_heatmap)",                False),
    ("digest.py",               "데이터 다이제스트(Codex 입력)",       False),
]

def need_data():
    import glob
    files = glob.glob(os.path.join(ROOT, "data", "*_arrivals_long.csv"))
    return files

def main():
    if not need_data():
        sys.exit("[중단] data/*_arrivals_long.csv 가 없습니다. 목적지 입국통계 패널을 data/ 에 두세요(data/README.md 참조).")
    os.makedirs(os.path.join(ROOT, "out", "figs"), exist_ok=True)
    print(f"[mk2] 보고서 생성 시작 · 플러그인 루트 = {ROOT}")
    t0 = time.time()
    for i, (script, desc, optional) in enumerate(STAGES, 1):
        print(f"  [{i}/{len(STAGES)}] {desc} … ({script})", flush=True)
        r = subprocess.run([sys.executable, os.path.join("scripts", script)], cwd=ROOT)
        if r.returncode != 0:
            if optional:
                print(f"  [건너뜀] {script} 선택 단계 실패(exit {r.returncode}) — 계속 진행.")
            else:
                sys.exit(f"[실패] {script} (exit {r.returncode})")
    dg = os.path.join(ROOT, "out", "data_digest.md")
    print(f"[mk2] 데이터 생성 완료 ({time.time()-t0:.0f}s) → {dg}")
    print("[mk2] 다음: Codex가 out/data_digest.md + out/figs/ 를 읽고 보고서를 작성한다(SKILL.md).")

if __name__ == "__main__":
    main()
