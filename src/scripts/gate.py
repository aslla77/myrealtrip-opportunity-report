"""
Stage 2-3 프로토타입 — 선행국의 '현재 행선지' 추적 + 한국 적용성(다음 목적지 후보)
- Stage 1(leadlag2.py) 결과에서 '한국을 먼저 간(유의) 선행국' L을 가져온다.
- Stage 2: L의 최근 12개월 입국 모멘텀(YoY)을 우리가 가진 모든 목적지에 대해 계산 → L이 지금 뜨는 목적지.
- Stage 3: 그 목적지에서 한국이 아직 뒤처졌는가(gap = L_YoY - KR_YoY >0) → '한국 다음 후보'.
         전이신뢰도 = L이 한국을 선행한 증거강도(Stage1 max z, 선행목적지수)로 가중.
정직성: 선행은 목적지별·단기라 약함 → 후보는 '근거 붙은 가설 랭킹', 최종판단은 사람.
"""
import glob, os
import numpy as np, pandas as pd
from leadlag import load_destination, ANCHOR

RS, RE = "2025-06-01", "2026-05-01"   # 고정 최근창(회복 후, 기저 정상화 → YoY 왜곡↓)
MIN_RECENT = 8      # 최근창 내 최소 유효월
YOY_CAP = 200.0     # YoY(%) 상한(코로나 저점 기저 폭발 방어)
HOT = 5.0
GAP = 5.0
LEADER_TOPK = 15    # 리더는 선도목적지에서 상위 K위 주요시장만(군소시장 잡음 제외)
LEADERS_CSV = "out/leaders_all_destinations.csv"
OUT = "out"

def recent_momentum(wide, s):
    if s not in wide.columns: return np.nan, None, None
    yoy = (wide[s].pct_change(12)*100).replace([np.inf,-np.inf], np.nan)
    yoy = yoy.clip(upper=YOY_CAP).loc[RS:RE].dropna()
    if len(yoy) < MIN_RECENT: return np.nan, None, None
    return float(yoy.mean()), f"{yoy.index.min():%Y-%m}", f"{yoy.index.max():%Y-%m}"

OPP_SHARE = 3.0     # 한국 점유율 < 이 값 → 저침투(기회 후보)
MATURE_SHARE = 8.0  # 한국 점유율 >= 이 값 → 이미 성숙/포화(기회 아님)

def kr_penetration(wide, anchor="South Korea"):
    """최근 가용 ~12개월 합 기준 한국 점유율(%)·순위."""
    recent = wide.dropna(how="all").iloc[-14:]
    tot = recent.sum()
    if tot.sum() == 0 or anchor not in tot.index: return np.nan, None
    share = (tot/tot.sum()*100).sort_values(ascending=False)
    return round(float(share[anchor]),1), int(list(share.index).index(anchor))+1

def market_rank(wide, s, win_s="2009-01-01", win_e="2019-12-01"):
    """선도목적지에서 s의 출발국 규모 순위(1=최대). preCOVID 평균 기준."""
    sub = wide.loc[win_s:win_e]
    if s not in sub.columns or sub[s].dropna().empty: return 9999
    means = sub.mean().sort_values(ascending=False)
    return int(list(means.index).index(s))+1 if s in means.index else 9999

def main():
    dests = {}
    for f in sorted(glob.glob("data/*_arrivals_long.csv")):
        name = os.path.basename(f).replace("_arrivals_long.csv","")
        dests[name] = load_destination(f)
    print("Stage2-3 목적지 패널:", list(dests.keys()))

    CREDIBLE_MAX_LEAD = 11   # >=12개월 단일목적지 선도는 허위양성(Estonia/UAE/Samoa)으로 제외
    lead_df = pd.read_csv(LEADERS_CSV)
    leaders = lead_df[(lead_df.went_first == True) &
                      (lead_df.lead_months <= CREDIBLE_MAX_LEAD)].copy()
    # 주요시장 필터: 리더가 '선도한 목적지'에서 상위 TOPK 출발국일 때만(군소시장 잡음 제외)
    def is_major(row):
        return market_rank(dests.get(row.dest, pd.DataFrame()), row.country) <= LEADER_TOPK
    leaders = leaders[leaders.apply(is_major, axis=1)]
    print(f"[필터] >=12개월 허위양성 제외 + 선도목적지 상위{LEADER_TOPK}위 주요시장만 → 신뢰 선행국 {leaders.country.nunique()}개")
    if not len(leaders):
        print("Stage1 신뢰 선행국 없음 — 중단."); return
    leader_nations = sorted(leaders.country.unique())
    transfer = (leaders.groupby("country")
                .agg(max_z=("z","max"), n_dest_led=("dest","nunique"),
                     avg_lead=("lead_months","mean"),
                     led_at=("dest", lambda s: ",".join(sorted(set(s))))).reset_index())
    print("\n선행국(한국을 먼저 간, Stage1 z>=3):")
    print(transfer.to_string(index=False))

    rows = []
    for L in leader_nations:
        tw = transfer[transfer.country==L].iloc[0]
        for dname, wide in dests.items():
            if dname == L: continue
            Lmom, ls, le = recent_momentum(wide, L)
            Kmom, ks, ke = recent_momentum(wide, ANCHOR)
            if np.isnan(Lmom) or np.isnan(Kmom): continue
            gap = Lmom - Kmom
            kr_sh, kr_rk = kr_penetration(wide)
            rows.append(dict(leader=L, dest=dname,
                             L_recent_yoy=round(Lmom,1), KR_recent_yoy=round(Kmom,1),
                             gap=round(gap,1), kr_share=kr_sh, kr_rank=kr_rk,
                             max_z=round(float(tw.max_z),1), led_at=tw.led_at, recent=f"{ls}~{le}"))
    cand = pd.DataFrame(rows)
    if not len(cand):
        print("\n후보 계산 불가(데이터 부족)."); return
    # 침투수준 게이트: 남들↑·한국 flat 이면서 한국이 저침투일 때만 '기회'
    def category(r):
        if pd.isna(r.kr_share): return "?"
        if r.kr_share >= MATURE_SHARE: return "성숙/포화(기회아님)"
        if (r.L_recent_yoy>=HOT) and (r.gap>=GAP) and (r.kr_share<OPP_SHARE): return "기회후보"
        return "중립"
    cand["category"] = cand.apply(category, axis=1)
    cand["is_candidate"] = cand.category=="기회후보"
    cand["score"] = (cand.L_recent_yoy.clip(lower=0) * cand.gap.clip(lower=0)
                     * cand.max_z.clip(lower=0)).round(1)
    cand = cand.sort_values(["is_candidate","score"], ascending=False)
    cand.to_csv(f"{OUT}/stage3_candidates.csv", index=False)

    print("\n================  한국 '다음 목적지' 기회후보 (선행국↑ & 한국 flat & 한국 저침투)  ================")
    cols=["leader","dest","L_recent_yoy","KR_recent_yoy","gap","kr_share","kr_rank","max_z","led_at","score"]
    c = cand[cand.is_candidate].drop_duplicates("dest")
    if len(c):
        print(c[cols].to_string(index=False))
    else:
        print("기회후보 없음.")
    print("\n[대조] 성숙/포화로 걸러진 목적지(한국 이미 큰 시장 — 오탐 방지):")
    mat = cand[cand.category=="성숙/포화(기회아님)"][["dest","kr_share","kr_rank"]].drop_duplicates("dest")
    print(mat.to_string(index=False) if len(mat) else "없음")
    print("\n주의: ①선행 근거 목적지별·단기(약함) ②베트남 등 gappy 데이터 ③최근창 2025~26 회복기 → '근거 붙은 가설', 최종판단 사람. 패널 클수록 신뢰↑.")

if __name__ == "__main__":
    main()
