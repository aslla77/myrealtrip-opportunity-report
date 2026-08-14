# data — 목적지 입국통계 패널 (스키마·출처·확장 타깃)

- 스키마(각 파일 `<Dest>_arrivals_long.csv`): `month(YYYY-MM), source_country, arrivals`
- 원천: 각 목적지 정부 공개통계(A급). 상세 출처·기준·확인일은 `../skills/opportunity-report/references.md`.
- **원천 CSV는 용량상 미포함** — 수집 스크립트로 재생성 원칙.

## 현재 패널 (13개 목적지)
Singapore, Japan, Australia, NewZealand, USA, Canada, Philippines, Thailand, Vietnam, Malaysia, Macao, Indonesia, Taiwan.
- 기준 혼재(거주지/국적/발급지) — 통합 시 소폭 오차. 도시 단위 통계 없음(전국 관문 좌표 `../geo/gateways.csv`로 근사).

## 검증된 확장 타깃 (Beta 실소스 검증 2026-07-05 · `research/마이리얼트립/beta-panel-expansion.md`)
> 조건: 월별 × 개별국(한국이 개별 행) × 무료조회. 수집 착수 권고 순위.

| 순위 | 목적지 | 소스·URL | 형식(파싱) | 한국 | 리스크 |
|---|---|---|---|---|---|
| 1 | **Maldives** | MoT "Arrivals by Nationality" · https://www.tourism.gov.mv/en/statistics/dashboard | PDF 정형표 (중) | #11 (2023-01 실측) | 대시보드 JS — PDF 직접 |
| 2 | **Guam** | GVB Arrivals Summary · https://www.guamvisitorsbureau.com/research/statistics/visitor-arrival-statistics | 웹/PDF (중) | **#1 출발국** | HTTP 403 봇차단 → 우회 필요 |
| 3 | **Sri Lanka** | SLTDA Monthly Reports · https://www.sltda.gov.lk/en/monthly-tourist-arrivals-reports | PDF (상, 국기그래픽) | #30 소량 | 파싱 난도 상 |

- **제외(정정) Hong Kong**: C&SD 650-80001 API를 실인출(2026-07-05, `full_series=1`)한 결과 **개별국이 아니라 12개 지역(대륙) 단위** — 한국은 "North Asia"에 묶여 분리 불가. HKTB PartnerNet은 개별시장 제공하나 **로그인/가입 필요**. → 무료·개별국 조건 **FAIL**. (Beta의 PASS는 표 제목 기반 추론이었고 실API로 반증됨.)
- **보류** Croatia DZS(`podaci.dzs.hr/2025/en/{code}` 월별 패턴): 한국 개별 행 미확인 + **숙박등록 기준**(입국통계와 개념 상이).
- **제외** Spain INE Frontur: 한국이 "Rest of the world"로 묶임(개별국 아님).

## 통합 주의
- **지표 정의 혼재**: 크로아티아=숙박등록 arrivals vs 나머지=입국통계 arrivals — 같은 'arrivals' 아님. 패널 통합 시 컬럼/주석에 기준 명시.
- 수집기 형식별 난이도: API/CSV(홍콩) < HTML/XLSX < PDF(몰디브·스리랑카). PDF는 표 추출 검증 필수.
