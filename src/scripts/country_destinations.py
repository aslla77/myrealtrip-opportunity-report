"""
country_destinations.py — '각 국별 많이 가는 여행지' (모든 출발국 → top 목적지)
현재 목적지 패널(수집된 목적지국의 출발국별 입국통계)에서, 각 출발국이 '패널 목적지 중'
어디를 가장 많이 가는지 최근 12개월 기준으로 랭킹. (패널 확장 시 자동으로 온전해짐.)
한계: 패널에 없는 목적지(중동·유럽 등 미수집)는 못 봄 → '패널 내 top'임을 명시.
출력: out/country_destinations.csv + country_travel_heatmap(주요 출발국×목적지 히트맵). 확인일 2026-07-05.
"""
import glob, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from leadlag import load_destination, norm_country, is_agg  # 동일 정규화 재사용

OUT="out"; FIG="out/figs"; os.makedirs(FIG, exist_ok=True)

def recent_sum_yoy(s, n=12):
    """최근 n개월 합 + 최근 YoY(전년동월 대비 최근 n개월 평균, %)."""
    s = s.dropna()
    if len(s) < n+1: return np.nan, np.nan
    recent = s.iloc[-n:]
    yoy = (s.pct_change(12)*100).replace([np.inf,-np.inf], np.nan).iloc[-n:].clip(-100,200)
    return float(recent.sum()), (float(yoy.mean()) if yoy.notna().sum()>=6 else np.nan)

def main():
    dests={}
    for f in sorted(glob.glob("data/*_arrivals_long.csv")):
        name=os.path.basename(f).replace("_arrivals_long.csv","")
        dests[name]=load_destination(f)   # index=ts, cols=source_country

    rows=[]
    for dest,w in dests.items():
        for c in w.columns:
            if is_agg(c): continue
            tot,yoy=recent_sum_yoy(w[c])
            if np.isnan(tot) or tot<=0: continue
            rows.append(dict(source_country=c, dest=dest, recent12_sum=tot, recent_yoy=yoy))
    df=pd.DataFrame(rows)
    # 각 출발국이 패널 내에서 어디를 많이 가나 → 목적지 순위 + 패널내 점유율
    df["panel_share"]=df.groupby("source_country")["recent12_sum"].transform(lambda s: s/s.sum()*100)
    df["dest_rank"]=df.groupby("source_country")["recent12_sum"].rank(ascending=False,method="first").astype(int)
    df=df.sort_values(["source_country","dest_rank"])
    df["recent12_sum"]=df["recent12_sum"].round(0); df["panel_share"]=df["panel_share"].round(1)
    df["recent_yoy"]=df["recent_yoy"].round(1)
    df.to_csv(f"{OUT}/country_destinations.csv",index=False)

    # 주요 출발국 top3 목적지(리드국 + 대형시장 대표)
    focus=["South Korea","Indonesia","Thailand","Japan","Taiwan","China","USA","Malaysia","Vietnam","Philippines"]
    focus=[c for c in focus if c in set(df.source_country)]
    print("=== 각 국별 많이 가는 여행지 (패널 내 top3, 최근 12개월) ===")
    for c in focus:
        top=df[(df.source_country==c)&(df.dest_rank<=3)]
        s=", ".join(f"{r.dest}({r.panel_share}%)" for _,r in top.iterrows())
        print(f"  {c:14s} → {s}")

    # ---- country_travel_heatmap: 주요 출발국 × 목적지 점유율 히트맵 ----
    piv=(df[df.source_country.isin(focus)]
         .pivot_table(index="source_country",columns="dest",values="panel_share",fill_value=0)
         .reindex(focus))
    piv=piv[piv.sum().sort_values(ascending=False).index]   # 목적지 열을 총량순 정렬
    fig,ax=plt.subplots(figsize=(12,5.2))
    im=ax.imshow(piv.values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=min(60,piv.values.max()))
    ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index, fontsize=9)
    for i in range(len(piv.index)):
        for j in range(len(piv.columns)):
            v=piv.values[i,j]
            if v>=8: ax.text(j,i,f"{v:.0f}",ha="center",va="center",fontsize=7.5,
                             color="white" if v>=30 else "black")
    ax.set_title("Where each source country travels within our destination panel\n"
                 "(share of its panel arrivals, recent 12 months; panel-limited — Mideast/Europe not yet collected)")
    fig.colorbar(im,ax=ax,label="% of country's arrivals within panel")
    fig.tight_layout(); fig.savefig(f"{FIG}/country_travel_heatmap.png",dpi=120); plt.close(fig)
    print("\nsaved:",f"{FIG}/country_travel_heatmap.png","+ out/country_destinations.csv")

if __name__=="__main__":
    main()
