"""
여행 트렌드 선행지표 발견기 v2 — "대체로 한국을 선도(lead)하는 국가" 탐지
목적지 여러 곳의 [출발국 x 월] 입국자 시계열을 모아:
  1) 계절성 제거(YoY 전년동월 대비)
  2) 각 목적지에서 '한국을 >=12개월 선행'하는 출발국 탐지 (lead-lag)
  3) 순환이동 순열검정으로 허위상관 방어 (paper 2502.19043 의 random-baseline 아이디어 차용)
  4) freshness: 선도국이 (한국이 따라갈 때) 아직 뜨는 중인지 / 이미 식었는지
  5) 목적지 전반 집계 -> '대체로 한국을 선도하는 나라' 랭킹
원칙: 한국이 선도/후행인지 단정 않고 데이터로 발견. 모든 수치는 실제 공개데이터에서 계산.
데이터 출처(A급): 각 목적지 정부통계 (data/references 참조). 확인일 2026-07-04.
"""
import glob, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 파라미터 (계절/주기 고려: 선도 최소 1년) ----
WIN_S, WIN_E = "2009-01-01", "2019-12-01"   # preCOVID 클린 구간 (COVID 공통충격 배제)
LMAX      = 24     # 탐색 시차 0~24개월
LEAD_MIN  = 12     # '선도' 인정 최소 시차 = 1년
R_THRESH  = 0.35   # 최소 상관
P_PERM    = 0.05   # 순열검정 유의수준(참고용)
Z_THRESH  = 3.0    # 순열 z-score 문턱(다중검정 방어: ~50개국 스캔 family-wise 통제)
N_PERM    = 500
SEED      = 42
MIN_N     = 48     # 상관 최소 표본(월)
MIN_MEAN  = 200    # 창 내 월평균 입국 < 이 값이면 미소시장으로 제외(노이즈)
MIN_COVER = 0.90   # 창 내 월 존재율 < 이 값이면 비연속으로 제외(예: 베트남 1~7월만)
ANCHOR    = "South Korea"
OUT = "out"; os.makedirs(OUT, exist_ok=True)

# ---- 국가명 정규화 (목적지별 표기 통일) ----
NORM = {
    "Korea, Rep.":"South Korea","Republic of Korea":"South Korea","Korea (South)":"South Korea",
    "Rep. of Korea":"South Korea","Korea, Republic of":"South Korea","Korea":"South Korea","KOR":"South Korea",
    "Viet Nam":"Vietnam","United States":"USA","United States of America":"USA","U.S.A.":"USA","US":"USA",
    "Hong Kong SAR":"Hong Kong","Hong Kong, China":"Hong Kong","Hong Kong SAR, China":"Hong Kong",
    "Chinese Taipei":"Taiwan","Taiwan, China":"Taiwan","Mainland China":"China","China, People's Republic of":"China",
    "United Kingdom of Great Britain and Northern Ireland":"United Kingdom","U.K.":"United Kingdom",
    "Russian Federation":"Russia","Russian Fed.":"Russia",
}
AGG_TOKENS = ("total","other markets","others","all ","subtotal","not identified","unspecified",
              "world","asia","europe","oceania","americas","africa","middle east","north asia",
              "southeast asia","greater china","south asia","west asia")

def norm_country(c):
    c = str(c).strip()
    return NORM.get(c, c)

def is_agg(c):
    cl = str(c).strip().lower()
    return any(tok in cl for tok in AGG_TOKENS) and cl not in ("south africa (rep of)","south africa")

# ---- 로드 ----
def load_destination(path):
    df = pd.read_csv(path, dtype={"month":str})
    df["source_country"] = df["source_country"].map(norm_country)
    df = df[~df["source_country"].map(is_agg)]
    df["arrivals"] = pd.to_numeric(df["arrivals"], errors="coerce")
    df["ts"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    df = df.dropna(subset=["ts"])
    wide = df.pivot_table(index="ts", columns="source_country", values="arrivals", aggfunc="sum").sort_index().asfreq("MS")
    return wide

# ---- 상관/시차 도구 ----
def _corr(a, b):
    m = ~(np.isnan(a) | np.isnan(b))
    if m.sum() < MIN_N: return np.nan, m.sum()
    a, b = a[m], b[m]
    if a.std() == 0 or b.std() == 0: return np.nan, m.sum()
    return float(np.corrcoef(a, b)[0,1]), int(m.sum())

def maxlag_r(kr, c, lmax=LMAX):
    """양방향 탐색. L>0: C가 한국을 L개월 선행 corr(KR_t, C_{t-L}); L<0: 한국이 C를 선행.
    전체 L in [-lmax,lmax] 중 상관 최대. (best_L, best_r, n). best_L>0 이라야 'C가 한국 선행'."""
    best = (0, np.nan, 0)
    n = len(kr)
    for L in range(-lmax, lmax+1):
        if L >= 0:
            a, b = kr[L:], c[:n-L]          # corr(KR_t, C_{t-L}) — C 먼저
        else:
            m = -L; a, b = kr[:n-m], c[m:]  # corr(KR_t, C_{t+m}) — 한국 먼저
        r, nn = _corr(a, b)
        if not np.isnan(r) and (np.isnan(best[1]) or r > best[1]):
            best = (L, r, nn)
    return best

def perm_pvalue(kr, c, r_obs, rng, n_perm=N_PERM, lmax=LMAX):
    """C를 순환이동(autocorr 보존, 정렬 파괴)한 null에서 max-lag r 분포 -> z, p_emp."""
    n = len(c)
    null = np.empty(n_perm)
    for i in range(n_perm):
        off = int(rng.integers(lmax+1, n-lmax-1))
        _, r, _ = maxlag_r(kr, np.roll(c, off), lmax)
        null[i] = r if not np.isnan(r) else -1
    mu, sd = np.nanmean(null), np.nanstd(null)
    z = (r_obs - mu)/sd if sd > 0 else np.nan
    p = float((np.sum(null >= r_obs)+1)/(n_perm+1))
    return z, p

def freshness(kr_yoy, c_yoy):
    """한국 YoY 상위 25% 시점에 C의 동시점 YoY 평균. >0 아직 뜨는중(동반), <0 이미 식음(뒷북)."""
    m = ~(np.isnan(kr_yoy) | np.isnan(c_yoy))
    kr, c = kr_yoy[m], c_yoy[m]
    if len(kr) < MIN_N: return np.nan
    hi = kr >= np.quantile(kr, 0.75)
    return float(np.mean(c[hi]))

def fresh_label(f):
    if np.isnan(f): return "-"
    if f > 5:  return "아직뜨는중(동반상승)"
    if f < -5: return "이미식음(뒷북)"
    return "중립"

# ---- 목적지별 분석 ----
def analyze(wide, dest, rng):
    full_idx = pd.date_range(WIN_S, WIN_E, freq="MS")   # 고정 132개월(창 실제 길이)
    lvl = wide.reindex(full_idx)
    n_months = len(full_idx)
    yoy = wide.pct_change(12)*100.0
    w = yoy.loc[WIN_S:WIN_E]
    if ANCHOR not in w.columns:
        print(f"[{dest}] SKIP: {ANCHOR} 없음"); return None
    kr_cover = lvl[ANCHOR].notna().sum()/n_months if n_months else 0
    if kr_cover < MIN_COVER:
        print(f"[{dest}] SKIP: 한국 시계열 연속성 부족(cover={kr_cover:.0%}, 창내 월결측) — 엄밀 lead-lag 부적합"); return None
    # 게이트: 미소시장/비연속 제외
    keep = []
    for c in w.columns:
        cover = lvl[c].notna().sum()/n_months if n_months else 0
        mean_v = lvl[c].mean()
        if c == ANCHOR or (cover >= MIN_COVER and mean_v >= MIN_MEAN):
            keep.append(c)
    dropped = w.shape[1]-len(keep)
    kr = w[ANCHOR].to_numpy()
    rows = []
    for c in keep:
        if c == ANCHOR: continue
        cv = w[c].to_numpy()
        L, r, n = maxlag_r(kr, cv)
        if np.isnan(r) or n < MIN_N: continue
        # 최적화: r<R_THRESH면 어차피 sig 불가 → 값비싼 순열검정 생략(결과 동일).
        if r >= R_THRESH:
            z, p = perm_pvalue(kr, cv, r, rng)
        else:
            z, p = np.nan, np.nan
        f = freshness(kr, cv)
        sig = (r >= R_THRESH) and (not np.isnan(z)) and (z >= Z_THRESH)
        qualifies = sig and (L >= LEAD_MIN)          # 엄격: 1년+ 선도
        went_first = sig and (L >= 1)                # 현실: 유의하게 '먼저 간' (단기 포함)
        rows.append(dict(dest=dest, country=c, lead_months=L, corr=round(r,2), n=n,
                         z=round(z,1) if not np.isnan(z) else np.nan, p_perm=round(p,3),
                         freshness=round(f,1) if not np.isnan(f) else np.nan,
                         fresh_label=fresh_label(f), went_first=went_first, leads_korea=qualifies))
    if not rows:
        print(f"[{dest}] SKIP: 유효 상관 쌍 없음(표본 부족)"); return None
    res = pd.DataFrame(rows).sort_values(["leads_korea","corr"], ascending=[False,False])
    res.to_csv(f"{OUT}/leaders_{dest}.csv", index=False)
    return res

def main():
    rng = np.random.default_rng(SEED)
    files = sorted(glob.glob("data/*_arrivals_long.csv"))
    print("목적지 파일:", [os.path.basename(f) for f in files])
    all_res = []
    for f in files:
        dest = os.path.basename(f).replace("_arrivals_long.csv","")
        wide = load_destination(f)
        span = f"{wide.index.min():%Y-%m}~{wide.index.max():%Y-%m}"
        lvlw = wide.reindex(pd.date_range(WIN_S, WIN_E, freq="MS")); nm=len(lvlw)
        kept = sum(1 for c in wide.columns if c==ANCHOR or
                   (lvlw[c].notna().sum()/nm>=MIN_COVER and lvlw[c].mean()>=MIN_MEAN))
        print(f"\n===== {dest}  ({span}, 원국가 {wide.shape[1]} → 게이트통과 {kept}) =====")
        res = analyze(wide, dest, rng)
        if res is None: continue
        all_res.append(res)
        # '한국보다 먼저 간' 유의 국가 (단기 포함), 선행개월 큰 순
        wf = res[res.went_first].sort_values("lead_months", ascending=False)
        print(f"  [{dest}] 한국보다 먼저 간 국가(유의, L>=1): {len(wf)}개")
        if len(wf):
            print(wf[["country","lead_months","corr","z","p_perm","freshness","fresh_label"]].to_string(index=False))
        lk = res[res.leads_korea]
        print(f"  -> 그중 >=12개월(1년+) 선도: {list(lk.country) if len(lk) else '없음'}")

    if not all_res: return
    big = pd.concat(all_res, ignore_index=True)
    big.to_csv(f"{OUT}/leaders_all_destinations.csv", index=False)

    # ---- 집계: 대체로 한국보다 '먼저 간' 나라 (유의, 단기 포함) ----
    def aggregate(mask, title, fname):
        q = big[mask]
        if not len(q):
            print(f"\n[집계] {title}: 해당 없음."); return
        agg = (q.groupby("country")
                 .agg(n_dest=("dest","nunique"), avg_lead=("lead_months","mean"),
                      avg_corr=("corr","mean"),
                      dests=("dest", lambda s: ",".join(sorted(set(s)))))
                 .reset_index().sort_values(["n_dest","avg_corr"], ascending=False))
        agg["avg_lead"]=agg["avg_lead"].round(1); agg["avg_corr"]=agg["avg_corr"].round(2)
        agg.to_csv(f"{OUT}/{fname}", index=False)
        print(f"\n================  {title}  ================")
        print(agg.to_string(index=False))

    aggregate(big.went_first, "대체로 한국보다 먼저 간 나라 (유의, 단기 포함)", "korea_wentfirst_aggregate.csv")
    aggregate(big.leads_korea, "그중 >=12개월(1년+) 선도 (엄격)", "korea_leaders_aggregate.csv")

if __name__ == "__main__":
    main()
