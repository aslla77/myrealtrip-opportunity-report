# 마이리얼트립 기회 목적지 보고서 생성기 — Codex 플러그인

- 플러그인: `myrealtrip-opportunity-report` (v0.2.0) · 스킬: `opportunity-report`
- 한 줄 정체: **"각 국별 많이 가는 여행지 + 한국에게 열린 기회"** 보고서를, 공개 통계로 계산하고 Codex가 작성한다.

---

## 이 스킬이 하는 일
마이리얼트립 MD·상품기획·소싱팀을 위해, Codex 스킬 `@opportunity-report` 한 번으로 **2섹션 보고서**를 만든다.
- **섹션 1 · 각 국별 많이 가는 여행지**: 13개 목적지국의 공개 입국통계(출발국별·월별)로 "어느 나라가 어디로 많이 가는지"를 히트맵·표로 보여준다.
- **섹션 2 · 한국에게 열린 기회**: "한국을 앞서 움직이는 리드국(인니·태국 등)이 몰리는데, **한국인은 아직 안 갔고(저침투), 가까워서 뻔한 것도 아닌(원거리)** 목적지"를 거리-보정으로 랭킹한다.

핵심 아이디어 — 한국인 목적지 1·2·3위(일본·베트남·대만)는 **그냥 가까워서** 큰 것(근접성 교란). 한국발 **거리(대권거리)로 보정**해, 가까워서 뜬 착시가 아닌 "멀어도 뜨는 진짜 기회"만 가려낸다.

## 워크플로우 (데이터는 파이썬, 보고서는 Codex)
**1부 · 데이터 생성** — `python scripts/generate_data.py` (결정론적·재현 가능):
0. `collect_arrivals.py` — 목적지별 최신 월을 확인해 **정부 발표지연보다 뒤처진 소스만** 공식 출처에서 재수집(자동 가능 소스; PDF·인터랙티브는 수동 갱신 URL 안내). 최신이면 캐시 사용.
1. `leadlag.py` — YoY로 계절 제거 후 양방향 시차 + 순열검정(z≥3)으로 '한국을 앞선 리드국' 통계 검증.
2. `gate.py` — 리드국이 뜨는 목적지 × 한국 점유율 → 기회(점유율<3%) / 포화(≥8% 제외) / 중립 분류.
3. `distance.py` — 관문 좌표로 대권거리·직항시간 부착 → 거리-보정 기회점수 + `opportunity_map.png`.
4. `country_destinations.py` — 모든 출발국의 top 목적지 → `country_travel_heatmap.png`.
5. `digest.py` — 위 산출을 `data_digest.md`(표·숫자)로 정리.

**2부 · 보고서 작성** — **Codex가 `data_digest.md` + 그림을 읽고 보고서를 직접 서술**한다. 통계는 항상 재현되고, 해석·제안은 매번 데이터에 맞춰 새로 쓰인다(고정 템플릿 아님).

## 실행 방법
```bash
# 데이터 생성(0단계 신선도 수집 포함) → 그다음 Codex가 보고서 작성
python scripts/generate_data.py
```
- 입력: `data/*_arrivals_long.csv`(13개국 번들 포함, 즉시 실행 가능). 뒤처진 소스는 0단계가 자동 갱신 시도.
- 필요: pandas·numpy·matplotlib(`requirements.txt`).
- Codex에서: 스킬 `@opportunity-report` 호출 → 1부 실행 후 Codex가 보고서 작성.

## 기대효과
- **다음 목적지를 남보다 먼저**: "이미 뜬 곳"이 아니라 "곧 뜰 후보"를 근거·거리와 함께 받아 **선제 편성·소싱** → 마진·차별화.
- **오추천 방지**: 근접성 교란(일본·베트남 등 가까운 포화시장)을 거리·침투 게이트로 걸러내 헛발질을 막는다.
- **주기 재실행 = 최신 유지**: 새 월치가 발표되면 0단계 수집이 갱신하므로, 다시 돌릴 때마다 최신 통계 기준으로 기회를 잡는 **레이더**가 된다.

## 데이터·출처·정직성
- 입국통계·좌표 = **A**(정부통계·공개 지리정보) / 직항시간 = **B·C**(항공시각표 대략치, 라벨).
- 모든 수치는 공개 통계에서 **코드 재계산**(LLM 추정 아님), seed 고정 → 재현 가능. 입국통계는 월별 갱신이라 수집은 '새 월치가 나오면 갱신'이다('매일'이 아님).
- 랭킹은 **근거 붙은 가설**이며 최종 편성 판단은 사람(MD). 국가 간 여행수요는 대체로 함께 움직이므로(동조화) 선행은 보조 근거로만 쓴다.
- 현재 **13개 목적지 패널** 한정(중동·유럽 등 미수집). 상세 출처: `src/skills/opportunity-report/references.md`.

## 구성
```
src/
├─ .codex-plugin/plugin.json          # 플러그인 매니페스트
├─ skills/opportunity-report/SKILL.md + references.md
├─ scripts/ generate_data · collect_arrivals · leadlag · gate · distance · country_destinations · digest
├─ geo/ gateways.csv(관문 좌표)
├─ data/ 13개국 입국통계 CSV + README.md
└─ requirements.txt
```
