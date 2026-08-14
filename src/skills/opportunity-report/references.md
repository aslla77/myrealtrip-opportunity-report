# 마이리얼트립 프로젝트 — 데이터·자료 출처 정본 (확인일 2026-07-04)

여행 트렌드 선행지표(Leading-Indicator) 발견기 + 한국 저침투×상승 목적지 탐지.
모든 수치는 아래 공개 출처에서 실제 다운로드·계산. 값 조작·추정 없음. 각 목적지 CSV = `prototype/data/<dest>_arrivals_long.csv` (month,source_country,arrivals).

## A. 목적지별 입국통계 (출발국×월별) — 전부 A급 정부/공식 통계

| # | 목적지 | 기준 | 기간 | Stage | 출처(공식) · KR 2019-07 sanity |
|--|--|--|--|--|--|
| 1 | 싱가포르 | 거주지 | 2008-01~2026-01 | 1·2 | SingStat/STB via data.gov.sg `d_7e7b2ee60c6ffc962f80fef129cf306e` · KR=59,119 |
| 2 | 일본 | **국적** | 2003-01~2026-05 | 1·2 | JNTO 訪日外客統計 `jnto.go.jp/statistics/data/_files/20260617_1615-5.xlsx` · KR=561,675 |
| 3 | 호주 | 거주지 | 2008-01~2026-04 | 1·2 | ABS OAD_COUNTRY API `data.api.abs.gov.au/rest/data/ABS,OAD_COUNTRY,1.0.0/06..10.M` · KR=20,930 |
| 4 | 뉴질랜드 | 거주국 | 1978-04~2026-04 | 1·2 | Stats NZ Infoshare 표 **ITM330801** (infoshare.stats.govt.nz) · KR=5,294 (YE합계 공식치 일치) |
| 5 | 미국 | 거주국(COR) | 2000-01~2026-05 | 1·2 | NTTO I-94 `trade.gov/i-94-arrivals-program` (Monthly Arrivals COR xlsx) · KR=222,906 |
| 6 | 캐나다 | 거주국 | 1972-01~2026-04 | 1·2 | StatCan 표 **24-10-0050** (pid 24100050) WDS CSV · KR=41,235 |
| 7 | 대만 | 거주지 | 2008-01~2026-05 | 1·2 | 交通部觀光署 "Visitor Arrivals by Residence" (stat.taiwan.net.tw) · KR=72,797 |
| 8 | 필리핀 | 거주국 | 2008-01~2023-10 | **1** | DOT via data.gov.ph "Visitor Arrivals" · KR=167,249 (연간합 자체검증 통과) |
| 9 | 태국 | 국적 | 2020-01~2026-05 | **2** | MOTS `mots.go.th` 월별 xlsx · (2020~; KR 2020-01=200,808) |
| 10 | 베트남 | 시장/국적 | 2009-01~2026-06(**1~7월만**) | (2·주의) | VNAT/GSO `vietnamtourism.gov.vn/getStatistic/international` · KR 2019-07=321,493 |
| 11 | 말레이시아 | 입국자(국적) | 2020-01~2024-10 | **2** | DOSM via data.gov.my `storage.data.gov.my/demography/arrivals.csv` · KR 2020-01=98,357 |
| 12 | 마카오 | 증명서 발급지 | 2017-01~2026-05 | **2** | DSEC TourismApi `dsec.gov.mo/TourismApi/GetHomecodeData` · KR=55,372 (2019총계 공식치 일치) |
| 13 | 인도네시아 | 여권국적 | 2017-01~2026-05 | **2** | BPS 표 var=1470 (bps.go.id) · KR=39,740 |

- **Stage 1**(선행국 탐지, preCOVID 2009–2019 연속 필요) = 싱가포르·일본·호주·뉴질랜드·미국·캐나다·대만·필리핀 **8개**.
- **Stage 2**(최근 모멘텀·침투수준) = 위 + 태국·말련·마카오·인니(+베트남 주의). 필리핀은 2023-10까지라 Stage 2 제외.

### 데이터 정의상 주의 (한계 — 반드시 명시)
- **기준 혼재**: 거주지(SG·AU·NZ·US·CA·TW·PH) vs 국적(JP·TH·ID) vs 증명서발급지(Macao). 재외국민 등 소폭 이질성 → 목적지 비교 시 감안.
- **확보 불가/제외**: 영국(ONS 월별=광역만, 연간에 한국 없음) · 베트남 8~12월(원천 미공개, gappy) · 태국·말련·인니·마카오 preCOVID 부재(2017/2020~).
- 도시 단위(다낭·발리·세부) 공개통계 없음 — 전부 전국(national) 시장별.
- 호주 원계열(비계절조정)·프라이버시 무작위반올림. 미국 I-94 항공 중심.

## B. 방법론 근거 문헌 (등급 B — arXiv preprint)
- Lee, Lim, Choi, Jeong (2025). *Global Streams, Local Currents: A Data Analysis on Global VOD Content Consumption.* arXiv:2502.19043v3 [physics.soc-ph], 2025-10-28. (로컬 `2502.19043v3.pdf`)
- 관계: 핵심(Louvain 동시점 군집)은 우리 lead-lag와 다름(반박). 차용 = ①문제 정당화(그들 Future work=국가간 확산 temporal dynamics=우리 기여) ②강건성: 랜덤 baseline 대비 유의성(→ 우리는 순환이동 순열검정 z-score) + 대체설정 일치성.

## C. 분석 방법 (재현 가능) — `prototype/`
- `leadlag2.py` (Stage 1): YoY(계절성 제거) → `corr(KR_t, C_{t-L})` L=0..24 → **순환이동 순열검정 z-score** → **z≥3 & r≥0.35** → freshness. 게이트: 창내 월존재율≥90%·월평균≥200·미소시장 제외. 다중검정 방어로 z≥3 + ≥12m 단일히트는 허위양성 처리.
- `project.py` (Stage 2–3): 선행국 L의 최근12개월(2025-06~2026-05 고정창) YoY 모멘텀을 전 목적지에서 → **한국 gap** + **한국 침투수준(점유율) 게이트**(≥8% 성숙/포화 제외, <3% 저침투 기회) → '한국 다음 목적지 기회후보'.

## D. 핵심 발견 (8개 Stage1 목적지 기준)
- **강건한 "1년(≥12개월) 선행국"은 없음.** z≥3에도 잔존한 Estonia/UAE/Samoa는 100+개국 스캔의 다중검정 허위양성(군소·단일목적지·무기전).
- 유의 신호는 **plausible 단기(1~5개월)**, 그러나 **어느 나라도 2개+ 목적지에서 일관 선도 못함** → 국가간 여행수요는 대체로 **동조화**.
- 실용 신호는 lead-lag 자체보다 **"세계적 상승 × 한국 저침투" 목적지 탐지**(침투 게이트가 베트남·일본 오탐 제거). 후보 예: 마카오(태국↑)·뉴질랜드(대만↑).
