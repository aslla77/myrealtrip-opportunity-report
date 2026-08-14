"""
mk2 — 거리-보정 기회 탐지 (그림3 계보 + 근접성 지표)
문제의식: 지금 한국인 목적지 1·2·3위(일본·베트남·대만)는 '가까워서' 큰 것 — 근접성 교란.
해법: 후보는 '우리를 리드하는 나라들이 가는 목적지'(stage3_candidates)로 채우고,
      각 목적지에 [한국발 대권거리(A급·좌표계산) + 대략 직항시간(B/C 라벨)]을 붙여
      '멀지만 뜨는데 한국은 아직 안 간' 진짜 기회를 근접성 교란에서 분리한다.
출력: 거리-보정 기회맵(opportunity_map) + 목적지 랭킹표(리드국이 가는 곳 기준). 확인일 2026-07-05.
좌표=공개 지리정보(A급, 계산으로 거리 결정론). 직항시간=항공시각표 대략치(B/C, 라벨 전용).
"""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT="out"; FIG="out/figs"; os.makedirs(FIG, exist_ok=True)
ICN=(37.4602,126.4407)   # 서울 인천공항

# 목적지 주요 관문 좌표(공개 지리정보 A급) + 대략 직항시간(시간, 항공시각표 B/C 라벨)
GATEWAY={
 "Japan":("Tokyo",35.68,139.69,2.5),      "Taiwan":("Taipei",25.03,121.56,2.5),
 "Macao":("Macao",22.16,113.55,3.5),       "Philippines":("Manila",14.60,120.98,4.5),
 "Vietnam":("Hanoi",21.03,105.85,5.0),     "Thailand":("Bangkok",13.75,100.50,6.0),
 "Malaysia":("Kuala Lumpur",3.14,101.69,6.5),"Singapore":("Singapore",1.35,103.82,6.5),
 "Indonesia":("Jakarta",-6.20,106.85,7.0), "Australia":("Sydney",-33.87,151.21,10.5),
 "USA":("Los Angeles",34.05,-118.24,11.0), "Canada":("Vancouver",49.19,-123.18,10.0),
 "NewZealand":("Auckland",-36.85,174.76,11.0),
}

def haversine_km(a,b):
    R=6371.0; la1,lo1,la2,lo2=map(np.radians,[a[0],a[1],b[0],b[1]])
    d=np.sin((la2-la1)/2)**2+np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2
    return float(2*R*np.arcsin(np.sqrt(d)))

def main():
    cand=pd.read_csv(f"{OUT}/stage3_candidates.csv")
    # 거리·시간 부착
    geo={d:(g[0], haversine_km(ICN,(g[1],g[2])), g[3]) for d,g in GATEWAY.items()}
    cand["gateway"]=cand["dest"].map(lambda d: geo.get(d,("?",np.nan,np.nan))[0])
    cand["dist_km"]=cand["dest"].map(lambda d: geo.get(d,("?",np.nan,np.nan))[1])
    cand["hours"]  =cand["dest"].map(lambda d: geo.get(d,("?",np.nan,np.nan))[2])

    # 목적지 레벨 집계: 리드국이 가는 곳 기준 — 최고 리드국 모멘텀, 최다 리드국 수
    g=(cand.groupby("dest")
         .agg(leaders=("leader",lambda s:",".join(sorted(set(s)))),
              n_leaders=("leader","nunique"),
              best_leader=("leader",lambda s: s.iloc[0]),
              leader_yoy=("L_recent_yoy","max"),
              kr_yoy=("KR_recent_yoy","first"),
              kr_share=("kr_share","first"), kr_rank=("kr_rank","first"),
              category=("category", lambda s: s.mode().iloc[0]),
              gateway=("gateway","first"), dist_km=("dist_km","first"), hours=("hours","first"))
         .reset_index())
    g["underpen"]=(8.0-g["kr_share"]).clip(lower=0)          # 저침투 강도(점유율 낮을수록↑)
    # 진짜 기회 점수: 리드국 모멘텀 × 저침투 × 거리가중(멀수록 '비자명') — 근접성 교란 보정
    g["far_w"]=(g["hours"]/g["hours"].max())
    g["opp_score"]=(g["leader_yoy"].clip(lower=0)*g["underpen"]*(0.5+g["far_w"])).round(1)
    g=g.sort_values("opp_score",ascending=False)
    g.to_csv(f"{OUT}/opportunity_mk2.csv",index=False)
    show=["dest","gateway","hours","dist_km","best_leader","n_leaders","leader_yoy","kr_yoy","kr_share","kr_rank","category","opp_score"]
    print("=== mk2 거리-보정 기회 랭킹 (리드국이 가는 목적지) ===")
    print(g[show].to_string(index=False))

    # ---- opportunity_map: 거리-보정 기회맵 ----
    CMAP={"기회후보":"#2b8cbe","성숙/포화(기회아님)":"#d7301f","중립":"#bdbdbd"}
    LAB ={"기회후보":"Opportunity (low KR share)","성숙/포화(기회아님)":"Saturated (KR already big)","중립":"Neutral"}
    fig,ax=plt.subplots(figsize=(11,6.6))
    ax.set_xlim(1.5,12.6); ax.set_ylim(-8,72)
    ax.axvspan(8.5,12.6, color="#2b8cbe", alpha=.05)          # 원거리 '진짜 기회' 존
    for cat,sub in g.groupby("category"):
        ax.scatter(sub["hours"], sub["leader_yoy"], s=(sub["underpen"]*60+40),
                   c=CMAP.get(cat,"#999"), edgecolor="k", linewidth=.5, alpha=.85,
                   label=LAB.get(cat,cat), zorder=3)
    for _,r in g.iterrows():
        dy = -18 if r.dest=="Macao" else 5                    # 마카오 라벨은 아래로(제목 겹침 방지)
        ax.annotate(f"{r.dest}\n(KR {r.kr_share}%·#{int(r.kr_rank)})",
                    (r.hours, r.leader_yoy), fontsize=7.5, xytext=(6,dy), textcoords="offset points")
    ax.axhline(5, color="gray", ls=":", lw=1)                 # HOT 문턱
    ax.annotate("FAR & RISING & low-KR\n= real opportunity\n(not just 'close & obvious')",
                (9.0,63), fontsize=9.5, color="#2b8cbe", fontweight="bold")
    ax.set_xlabel("Travel time from Korea (approx. direct-flight hours; great-circle distance basis)")
    ax.set_ylabel("Leader-nation recent momentum (max YoY %, 2025-06~2026-05)")
    ax.set_title("mk2 Distance-adjusted opportunity map\n"
                 "Candidates = destinations the nations that LEAD Korea are flowing into.\n"
                 "Bubble size = Korea under-penetration (bigger = lower KR share). Close-but-obvious (left) vs far-but-real (right).")
    ax.grid(alpha=.3); ax.legend(loc="lower left", fontsize=9, title="Penetration gate")
    fig.tight_layout(); fig.savefig(f"{FIG}/opportunity_map.png", dpi=120); plt.close(fig)
    print("\nsaved:", f"{FIG}/opportunity_map.png")

if __name__=="__main__":
    main()
