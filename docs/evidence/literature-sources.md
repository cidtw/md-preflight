# 문헌·기관 출처 목록

> 시연·보고서 인용용. URL은 2026-07-19 기준 접근 가능 여부 확인.  
> **등급**: ★★★ 1차/공신력 높음 · ★★ 실무·교재 관례 · ★ 보조/해설.

---

## A. 재고이론 핵심 (ROP · Safety Stock · Service Level)

### A1. Peter L. King, CSCP — “Understanding safety stock and mastering its equations”
- **매체**: APICS magazine, July/August 2011  
- **미러**: MIT 2.810 수업 자료  
  https://web.mit.edu/2.810/www/files/readings/King_SafetyStock.pdf  
- **등급**: ★★★  
- **핵심 인용 가능 내용**:
  - Cycle service level(CSL)과 Z-score 표:  
    90%→1.28 · 95%→1.65 · 97%→1.88 · 98%→2.05 · 99%→2.33 · 99.9%→3.09  
  - 수요 변동만 있을 때:  
    \( SS = Z \times \sqrt{PC/T_1} \times \sigma_D \)  
    (PC = performance cycle ≈ 리드타임+리뷰, \(T_1\) = σ 산정 기간)  
  - 리드타임 변동: \( SS = Z \times \sigma_{LT} \times D_{avg} \)  
  - 독립 시 결합: 제곱합 루트  
  - 전형적인 CSL 목표 구간 **90–98%**  
  - “감으로 안전재고 잡기 / 사이클스톡의 10–20%”는 성능이 나쁘다 → **수식 정당화** 필요  
- **본 서비스 매핑**: `SERVICE_LEVEL_Z` (1.28 / 1.65 / 2.33) · 통계 SS의 \(Z \times \sqrt{\cdot}\) 골격

### A2. ASCM (구 APICS) — Safety stock / Z-factor 실무 가이드
- **URL**: https://www.ascm.org/ascm-insights/safety-stock-a-contingency-plan-to-keep-supply-chains-flying-high/  
- **등급**: ★★★ (업계 공인 기관 인사이트)  
- **핵심**:
  - \( SS = Z \times \sigma_D \) (리드타임 수요 표준편차)  
  - CSL 예: 98% → Z≈2.05; 목표를 90%로 내리면 Z≈1.28 수준으로 SS 대폭 감소 가능  
  - 기간이 다른 σ는 \(\sqrt{\text{기간비}}\) 로 스케일 (King과 동일)  
- **본 서비스 매핑**: 정책 Z 선택 UI · “SL↑ → SS↑” 서사

### A3. 표준 ROP 정의 (실무 합의형)
- **형태**:  
  \( \mathrm{ROP} = (\text{평균 일수요} \times \text{리드타임 일수}) + \text{Safety Stock} \)  
- **대표 2차 출처** (동일 식 반복 확인용):
  - Netstock: https://www.netstock.com/blog/reorder-point-formula/  
  - NetSuite: https://www.netsuite.com/portal/resource/articles/inventory-management/reorder-point-rop.shtml  
  - inFlow: https://www.inflowinventory.com/blog/reorder-point-formula-safety-stock/  
- **등급**: ★★ (실무 표준; 학술 원형은 Silver/Pyke/Peterson · Chopra · Axsäter 계열 교재)  
- **본 서비스 매핑**: `ROP = D_eff * LT + SS` (`engine.py`)

### A4. √Lead-time 스케일 (분산 합의)
- 독립·동일 기간 수요라면 리드타임 L 기간 합의 분산 = L·σ² → 표준편차 = σ√L  
- 해설: CrossValidated “Why square root of lead time…”  
  https://stats.stackexchange.com/questions/448999/why-square-root-of-leadtime-during-safety-stock-calculation  
- King/ASCM의 \(\sqrt{PC/T}\) 와 동형  
- **등급**: ★★★ (통계 기초)  
- **본 서비스 매핑**: `math.sqrt(lead_time_days * vol_norm)` in `store_safety_stock`

### A5. 고전 식의 한계 (정직 인용)
- Nicolas Vandeput — classical \( Ss = z\,\sigma\sqrt{L(+R)} \) 가정의 한계  
  https://nicolas-vandeput.medium.com/outgrowing-the-safety-stock-formula-112e4efb9bf5  
- **등급**: ★★  
- **시연 활용**: “우리는 고전 정규 근사를 쓰되, POS σ·LT 분포가 생기면 고도화”라고 한계를 먼저 말함

### A6. SLR — Safety stock OR 모델 리뷰
- Gonçalves et al., *Operations research models and methods for safety stock determination*, 2020  
  PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC7550265/  
- **등급**: ★★★  
- **시연 활용**: “안전재고 차원화는 활발한 OR 연구 주제이며, 기본 출발점은 서비스레벨·변동·리드타임”

---

## B. 서비스 레벨 · Z 표 (재확인)

| Cycle service level | Z (표준정규) | 출처 |
|---------------------|--------------|------|
| 84% | 1.00 | King Fig.2 |
| 90% | **1.28** | King · demandplanning.net 표 · 다수 ERP 관례 |
| 95% | **1.65** | King · ASCM 해설 |
| 98% | 2.05 | King · ASCM |
| 99% | **2.33** | King |
| 99.9% | 3.09 | King |

**본 서비스 채택**: 90 / 95 / 99% → 1.28 / 1.65 / 2.33 (`domain_catalog.SERVICE_LEVEL_Z`)  
**주의**: 이는 **cycle service level** 근사다. **Fill rate**(수량 충족률)와는 다르다 (King Fig.3).  
UI 카피는 “품절 방어 수준”으로 풀어쓰되, 전문 토글에서는 CSL임을 명시한다.

---

## C. 리드타임 (LT) — 고정 입력 정당화

### C1. 이론적 구분
- **Lead time (L)**: 발주 → 입고까지 시간. ROP의 **곱하는 상수**(평균 LTD = D·L).  
- **Lead-time variability (σ_LT)**: 안전재고 **가산** 항 (King: \(Z \sigma_{LT} D\)).  
- **본 서비스 설계**:
  - 계약/품목 표준 L → **입력 유지, 추천 변경 없음**  
  - 접근성·상권 지연 신호 → **리스크 일수 × D = 버퍼 재고** (σ_LT 항의 단순·해석 가능 proxy)

### C2. 국내 편의점·유통 관행 (2차·사례)
- 편의점 물류는 전통적으로 **일배(日配)** · 발주→입고 **당일~익일(≤1일 전후)** 경쟁 서사가 다수  
  - 예: LG25/GS 계열 물류 사례 서술 (리드타임 12시간~하루 이내 강조, 업계 사례 글)  
- 채널이 커질수록(슈퍼→SSM→하이퍼) **센터·벤더·교차도크** 구조로 **발주 주기·납품 창**이 길어지는 것이 일반적  
- **본 서비스 기본 LT** (`DEFAULT_STANDARD_LT`):  
  편의 1.5 · 슈퍼 2.0 · SSM 2.5 · 하이퍼 3.0 (일)  
  → “국내 일배/주간 납품 관행의 **엔지니어링 디폴트**”; 실제 계약이 있으면 입력 우선  
- **등급**: ★ (관행·사례; 공개 통계 전수 조사는 아님) → 시연에서 “입력 우선 · 디폴트는 채널 관례”

---

## D. 발주량 · 주기 (Q · cycle)

### D1. 주기 검토(periodic review) / 사이클 스톡
- 고정 요일 발주(월수금 등)는 **periodic review** 에 가깝다.  
- 한 사이클 소진 ≈ \( D \times R \) (R = review/cycle days)  
- 목표 재고(order-up-to) 계열: \( S \approx D(R+L) + SS \) 등 (교재·실무 튜토리얼 다수)  
- **본 서비스**:  
  - `Q ≈ D_eff × cycle_days` (사이클 커버 물량 근사)  
  - ROP는 연속검토형 트리거, Q·요일은 **운영 레버**로 분리  
- **등급**: ★★

### D2. EOQ
- \( EOQ = \sqrt{2DS/H} \) — 주문비·재고비 균형  
- **본 서비스 비채택 이유**: 점포 단가 주문비·보유비 미입력. CAPA 제약이 EOQ보다 현실적.  
- 시연: “완전 EOQ가 아니라 **공간·발주 요일 제약 하의 커버리지 Q**”

### D3. CAPA 상한
- 소매 현장: 매대·후방고 **물리 용량**이 ROP/Q의 hard constraint  
- 이론 연결: constrained inventory / shelf-space allocation (광의)  
- **본 서비스**: `max_rop_for_capa` cover_days 테이블 — **engineering** (L3)  
- **등급**: ★ (현장 상식 + 내부 테이블; 공개 용량 표준 아님)

---

## E. 입지 · 경쟁 · 유동 (Geo)

### E1. Huff gravity model (1963/1964)
- 소비자가 점포 j를 고를 확률 ∝ 매력도 / 거리^β  
- Esri ArcGIS Business Analyst 문서:  
  https://pro.arcgis.com/en/pro-app/latest/tool-reference/business-analyst/understanding-huff-model.htm  
- Wikipedia: https://en.wikipedia.org/wiki/Huff_model  
- **등급**: ★★★ (소매 입지 고전)  
- **본 서비스 매핑**:
  - 경쟁: `exp(-d/decay) * tier_w * rank_decay` — 거리 감쇠 **형태**만 차용  
  - β·매장면적 매력도는 미추정 → intensity soft-sat 후 수요 계수 ≤1  
  - 상권 반경: 업태별 primary catchment 관례 (CVS 300m급 · 슈퍼 500m · SSM 1km · 대형 수 km) — 국내 상권분석 실무 관례 수준

### E2. 거리 감쇠 · 유동 POI
- 교통·앵커 시설 근접 → 보행/유입 증가 (도시·소매 입지 문헌 일반)  
- **본 서비스 FTI**: `w(cat) * exp(-d/250) * 0.5^rank` + soft saturation  
- **등급**: ★★ 형태 / ★ 계수(250m, half-sat 2.4)  
- 행사 uplift 200m · max +35%: **임시 수요 충격 proxy** (실시간 티켓 캘린더 없음)

### E3. 경쟁 포화
- 동일 상권 내 점포 밀도↑ → 점당 수요 분산 (Huff 경쟁항 · market share)  
- **본 서비스**: max −40% demand at intensity=1 (`COMPETITION_DEMAND_MAX_FRAC`)  
- **등급**: ★ cap 값; 형태는 ★★★

---

## F. 국내·규제·업태 참고 (보조)

| 주제 | 메모 | 등급 |
|------|------|------|
| 편의점 면적 구간 | 본 서비스 `STORE_SIZE` 밴드는 UI/채점용 구간; 공식 통계 분류와 1:1 아님 | ★ |
| 공정위·상권 반경 논의 | 대규모점포·SSM 규제·상권 이슈는 반경 감각의 **배경**; 법조문 직접 인용은 시연 시 신중 | ★ |
| GS/CVS 물류 혁신 사례 | 일배·LT 단축 스토리 — 채널 기본 LT 서사 보강 | ★ |

---

## G. 교재 원전 (시간 되면 직접 페이지 인용 권장)

| 저자 | 제목 | 관련 장 |
|------|------|---------|
| Silver, Pyke, Peterson / Thomas | Inventory Management and Production Planning… | Continuous review (s,Q), service levels |
| Chopra, Meindl | Supply Chain Management | Safety inventory, ROP |
| Axsäter | Inventory Control | Continuous/periodic review |
| Cachon, Terwiesch | Matching Supply with Demand | Newsvendor · service |

본 저장소는 저작권상 교재 전문을 복제하지 않는다. 시연에서는 **King(APICS) PDF + ASCM + ROP 표준식**을 1차 공개 근거로 쓰고, 교재명은 “동일 골격의 학부/MBA 표준”으로 언급한다.

---

## H. 인용 우선순위 (발표 슬라이드 / 질의응답)

1. **King (APICS 2011) PDF** — Z 표 · SS 식 · CSL vs fill rate  
2. **ASCM safety stock insight** — 기관 권위 · √기간 스케일  
3. **ROP = LTD + SS** — 실무 합의 (NetSuite 등)  
4. **Huff (1964)** — 경쟁·거리 감쇠 형태  
5. **본 서비스 L3 assumption 표** — `evidence-matrix.md`  
6. Vandeput — 고전 식 한계 (방어적 정직함)
