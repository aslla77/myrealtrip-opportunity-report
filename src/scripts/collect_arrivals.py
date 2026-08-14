"""
collect_arrivals.py — 입국통계 '신선도 게이트 + 수집' 레이어 (검색 관심도 대체)
generate_data.py 의 0단계. 목적지별 data/<Dest>_arrivals_long.csv 의 최신 월을 확인해
  · 충분히 최신이면        → 캐시 그대로 사용(수집 생략, 결정론 유지)
  · 발표지연보다 뒤처졌으면 → 공식 소스에서 재수집 시도
        - 자동 가능 소스(직접 CSV / 공개 REST API): 실제로 받아서 CSV 갱신
        - PDF·인터랙티브 포털 소스: 자동 불가 → 수동 갱신 URL만 안내(캐시 유지)
!!! 어떤 경우에도 실패로 파이프라인을 죽이지 않는다(수집 실패 → 캐시 사용 → 분석 계속).
    입국통계는 월별(정부 발표 지연 통상 1~3개월) 갱신이라 '매일 새 데이터'는 성립하지 않는다.

정직성(coder rule 준수): 아래 자동 수집기는 공식 엔드포인트 스키마에 맞춰 작성했으나
  네트워크 응답 실측 검증 전이다 → 각 소스 auto 라벨과 함께 '실행 검증 필요'로 표기.
  스키마가 어긋나면 예외처리로 캐시 폴백하므로 값 조작은 발생하지 않는다.
출처 상세: skills/opportunity-report/references.md (A급 정부/공식 통계).
"""
import os, sys, io, csv, json, glob, datetime, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Mozilla/5.0 (mrt-opportunity-report collector)"}
GRACE_MONTHS = 1  # 발표지연에 더해 이만큼 더 여유를 준 뒤에야 '뒤처짐'으로 본다


# ---------- 월 유틸 ----------
def ym_to_int(ym):
    y, m = ym.split("-")[:2]
    return int(y) * 12 + (int(m) - 1)

def cur_month_int():
    t = datetime.date.today()
    return t.year * 12 + (t.month - 1)

def csv_latest_month(dest):
    p = os.path.join(DATA, f"{dest}_arrivals_long.csv")
    if not os.path.exists(p):
        return None
    latest = None
    with open(p, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            mi = ym_to_int(row["month"])
            if latest is None or mi > latest:
                latest = mi
    return latest

def http_get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def write_long(dest, rows):
    """rows = iterable of (month 'YYYY-MM', source_country, arrivals). 원천 raw 국가명 그대로.
    분석부(norm_country/is_agg)가 정규화하므로 여기서 국가명 통일은 불필요."""
    rows = [(m, c, a) for (m, c, a) in rows if m and c and a not in (None, "")]
    if not rows:
        raise ValueError("수집 결과 0행")
    p = os.path.join(DATA, f"{dest}_arrivals_long.csv")
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "source_country", "arrivals"])
        w.writerows(rows)
    return len(rows)


# ---------- 자동 수집기 (직접 CSV / 공개 REST) · 실행 검증 필요 ----------
def collect_malaysia():
    # DOSM via data.gov.my — 직접 CSV. 스키마 추정: date(YYYY-MM-01), country, arrivals.
    raw = http_get("https://storage.data.gov.my/tourism/arrivals_country.csv")
    rd = csv.DictReader(io.StringIO(raw.decode("utf-8", "replace")))
    cols = {c.lower(): c for c in (rd.fieldnames or [])}
    dcol = cols.get("date") or cols.get("month")
    ccol = cols.get("country") or cols.get("nationality") or cols.get("source_country")
    acol = cols.get("arrivals") or cols.get("value") or cols.get("visitors")
    if not (dcol and ccol and acol):
        raise ValueError(f"예상 밖 컬럼: {rd.fieldnames}")
    out = []
    for row in rd:
        d = str(row[dcol])[:7]  # YYYY-MM
        out.append((d, row[ccol], row[acol]))
    return out

def collect_singapore():
    # data.gov.sg datastore — 국제방문객 by country/month. resource_id=references.md.
    rid = "d_7e7b2ee60c6ffc962f80fef129cf306e"
    url = f"https://data.gov.sg/api/action/datastore_search?resource_id={rid}&limit=100000"
    d = json.loads(http_get(url).decode("utf-8", "replace"))
    recs = d["result"]["records"]
    out = []
    for rec in recs:
        month = rec.get("month") or rec.get("Month")
        # 국가 컬럼은 데이터셋마다 다름 → month 외 첫 문자열/숫자쌍 탐색
        country = rec.get("level_2") or rec.get("country") or rec.get("Country")
        val = rec.get("value") or rec.get("Value") or rec.get("arrivals")
        if month and country and val not in (None, "", "na", "-"):
            out.append((str(month)[:7], country, val))
    return out

def collect_macao():
    # DSEC TourismApi — JSON. 스키마 실측 전 → 유연 파싱, 실패 시 예외.
    url = "https://www.dsec.gov.mo/TourismApi/GetHomecodeData"
    d = json.loads(http_get(url).decode("utf-8", "replace"))
    recs = d if isinstance(d, list) else d.get("data") or d.get("Data") or []
    out = []
    for rec in recs:
        month = rec.get("Period") or rec.get("period") or rec.get("month")
        country = rec.get("Country") or rec.get("country") or rec.get("Place")
        val = rec.get("Value") or rec.get("value") or rec.get("arrivals")
        if month and country and val not in (None, ""):
            out.append((str(month)[:7], country, val))
    return out


# ---------- 소스 레지스트리 ----------
# auto: 수집 함수 or None(자동 불가→수동 안내). lag: 통상 발표지연(개월). fmt: 원천 형식.
SOURCES = {
    "Malaysia":   dict(auto=collect_malaysia,  lag=3,  fmt="CSV(data.gov.my)",
                       url="https://storage.data.gov.my/tourism/arrivals_country.csv"),
    "Singapore":  dict(auto=collect_singapore, lag=2,  fmt="REST(data.gov.sg)",
                       url="https://data.gov.sg/datasets (d_7e7b2ee6...)"),
    "Macao":      dict(auto=collect_macao,     lag=2,  fmt="REST(DSEC TourismApi)",
                       url="https://www.dsec.gov.mo/TourismApi/GetHomecodeData"),
    # 자동 불가(형식 난이도·봇차단·인터랙티브 포털) → 수동 갱신 안내. references.md 참조.
    "Japan":      dict(auto=None, lag=2, fmt="XLSX(월별 URL)",   url="https://www.jnto.go.jp/statistics/data/"),
    "Australia":  dict(auto=None, lag=2, fmt="SDMX API",        url="https://data.api.abs.gov.au/rest/data/ABS,OAD_COUNTRY,1.0.0/06..10.M"),
    "NewZealand": dict(auto=None, lag=2, fmt="Infoshare(인터랙티브)", url="https://infoshare.stats.govt.nz (ITM330801)"),
    "USA":        dict(auto=None, lag=3, fmt="XLSX(I-94)",       url="https://www.trade.gov/i-94-arrivals-program"),
    "Canada":     dict(auto=None, lag=2, fmt="WDS zip-CSV",      url="https://www150.statcan.gc.ca (표 24-10-0050)"),
    "Taiwan":     dict(auto=None, lag=2, fmt="포털 표",          url="https://stat.taiwan.net.tw"),
    "Thailand":   dict(auto=None, lag=2, fmt="XLSX(월별)",       url="https://www.mots.go.th"),
    "Vietnam":    dict(auto=None, lag=2, fmt="포털 표(gappy)",   url="https://vietnamtourism.gov.vn/getStatistic/international"),
    "Indonesia":  dict(auto=None, lag=2, fmt="BPS 표(var=1470)", url="https://www.bps.go.id"),
    "Philippines":dict(auto=None, lag=99, fmt="data.gov.ph(2023-10 종료)", url="https://data.gov.ph"),
}


def main():
    files = glob.glob(os.path.join(DATA, "*_arrivals_long.csv"))
    if not files:
        print("[collect] data/*_arrivals_long.csv 없음 — 수집 대상 없음(분석부에서 중단됨).")
        return 0
    cur = cur_month_int()
    fresh, refreshed, stale_manual, failed = [], [], [], []
    for dest, meta in SOURCES.items():
        latest = csv_latest_month(dest)
        if latest is None:
            continue  # 패널에 없는 목적지
        expected = cur - meta["lag"] - GRACE_MONTHS  # 이 월까지는 나와있어야 '최신'
        if latest >= expected:
            fresh.append(dest)
            continue
        behind = expected - latest
        if meta["auto"] is None:
            stale_manual.append((dest, behind, meta))
            continue
        try:
            n = write_long(dest, meta["auto"]())
            refreshed.append((dest, n))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, Exception) as e:
            failed.append((dest, f"{type(e).__name__}: {e}", meta))

    print(f"[collect] 신선도 확인 {len([d for d in SOURCES if csv_latest_month(d) is not None])}개 목적지 · 기준월={cur}")
    if fresh:
        print(f"  · 최신(캐시 사용) {len(fresh)}: {', '.join(fresh)}")
    for dest, n in refreshed:
        print(f"  · [수집완료] {dest}: {n}행 갱신 ({SOURCES[dest]['fmt']}) — 실행 검증 필요")
    for dest, behind, meta in stale_manual:
        print(f"  · [수동 갱신 필요] {dest}: {behind}개월 뒤처짐 · {meta['fmt']} · {meta['url']} (캐시로 계속)")
    for dest, err, meta in failed:
        print(f"  · [수집 실패→캐시] {dest}: {err} · 수동: {meta['url']}")
    print("[collect] 완료 — 수집 실패/수동 항목은 캐시로 분석 계속. 자동 수집기는 Codex 첫 실행에서 검증할 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
