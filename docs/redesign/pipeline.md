# 파이프라인 계약 — ROP Adjust

```
[클라이언트 폼]
    │ parameters JSON
    ▼
┌──────────────┐     ┌──────────────────────────┐     ┌──────────────────┐
│ 1. INPUT     │ ──► │ 2. ANALYZE (internal)    │ ──► │ 3. OUTPUT        │
│ 템플릿 검증  │     │ 점수 + KB + LT/ROP 공식  │     │ 비교·근거 리포트 │
└──────────────┘     └──────────────────────────┘     └──────────────────┘
```

사용자 UX는 1 → (짧은 로딩) → 3. 2는 내부 전용.

## 1. Input (`app/pipeline/input`)

| 키 | 설명 |
|----|------|
| `product_name` | 최적화 품목 |
| `store_type` | 편의점 / 슈퍼 / SSM / 대형마트 |
| `store_size` | 연면적 구간 |
| `avg_ticket` | 객단가 구간 |
| `location_dong` | 행정동 |
| `use_precise_location` | (선택) 정확한 위치 사용 체크 |
| `store_address` | 정확한 매장 주소 — 체크 시에만 필수 |
| `consider_temp_foot_traffic` | (선택) 일시 유동인구 증분 — **정확한 주소 사용 시에만**. 주소 반경 200m 행사·유동 시설 검색 → 수요 배수 |
| `consider_competition_saturation` | (선택) 경쟁 포화·수요 분산 — **정확한 주소 사용 시에만**. 업태별 1차 상권 반경 내 경쟁 점포 거리·인접도 → 수요 계수(≤1) |
| `trade_area` | 상권 유형 |
| `accessibility` | 대로변 / 이면 / 건물 내 |
| `daily_demand` | 일평균 소진량 |
| `standard_lead_time_days` | (선택) **품목별** 표준/계약 LT — 입력 유지, 출력에서 변동 추천 없음 |
| `service_level` | (선택) 목표 서비스 레벨 90/95/99% → 정책 Z |
| `order_day_pattern` | (선택) 발주 요일 패턴(자동·화목·월수금 등) |
| `standard_rop` | (선택) 사내/업계 표준 ROP |
| `demand_sigma_daily` | (선택, R16) POS 일 수요 표준편차 σ → SS = Z·σ·√LT·w (vol proxy 비활성) |
| `measured_logistics_delay_days` | (선택, R16) 실측 추가 지연(일) → KB hash residual 대체 · 접근성 성분은 유지 |

불일치 안내:

- 유형 vs 규모 상이 → **규모** 기준 연산 + guidance  
- 유형 vs 객단가 상이 → **객단가** 기준 연산 + guidance  

## 2. Analyze (`app/pipeline/analyze`)

1. **스코어링 테이블** (`scoring.py`) — CAPA, 수요집중, 회전가중, 공급난이도, 수요변동, 접근성 리스크(일)  
2. **(선택) Kakao Local 보강** (`geo_enrichment.py`) — 주소 검색 + 카테고리/키워드 POI → `foot_traffic_index`  
   - **(선택) 일시 유동 스캔** (`event_foot_traffic.py`) — `consider_temp_foot_traffic` + 정확한 주소 시, 반경 **200m** 내 경기장·공연장·전시장·컨벤션 등 키워드 검색 → `event_foot_traffic_uplift` · `event_demand_multiplier`  
   - **(선택) 경쟁 포화 스캔** (`competition_saturation.py`) — `consider_competition_saturation` + 정확한 주소 시, 업태별 1차 상권(CVS 300m · 슈퍼 500m · SSM 1km · 대형 5km) 내 동종·위협 경쟁 거리·인접도 → `competition_intensity` · `competition_demand_factor(≤1)`  
3. **KB 매칭** (`knowledge_base.py`) — 행정동+품목+상권 시드 + (구조 FTI + 행사 블렌드) 기반 물류지연·Z계수·서술  
4. **공식** (`engine.py`) — SSOT; 상세는 `docs/architecture.md` 와 동기화

```
foot_traffic_index = soft_sat(
  Σ_{cat, rank≤N_cat} w(cat) * exp(-d/250) * 0.5^rank
)  where soft_sat(raw) = raw / (raw + 2.4) → (0,1)
  N_cat: rail/bus/anchor/… 최근접 1~2곳, CS2=convenience 저가중
# Optional temporary event-crowd (precise address only, r=200m):
event_uplift = soft_sat(Σ kind_w * exp(-d/100) * 0.5^rank_kind)
event_demand_multiplier = 1 + 0.35 * event_uplift   # max +35% demand
# Optional competition saturation (precise address only; industry radii):
competition_intensity = soft_sat(Σ tier_w * exp(-d/decay) * 0.5^rank_tier)
  tier_w: direct=1.0 · threat=0.85 · indirect=0.40
competition_demand_factor = 1 − 0.40 * intensity     # max −40% demand
D_eff = D * event_demand_multiplier * competition_demand_factor
  # 미옵션 시 각 배수=1 → D_eff=D
FTI_kb = min(1, FTI + 0.20 * event_uplift)
# LT is product input (kept as-is). Output never recommends changing LT.
LT = 입력 품목 표준 LT   # 고정 — 조정 레버 아님
Z = 서비스레벨 정책 Z(90/95/99) + 맥락(변동성·품목·FTI_kb)
물류 리스크일 = max(0, 접근성 성분 + KB 상권·행정동 리스크)
물류 버퍼개 = D_eff * 물류 리스크일
통계 안전재고 = Z * D_eff * sqrt(LT * vol/5) * 회전가중치   # 기본 L3 proxy
  # R16 if demand_sigma_daily: Z * σ_D * sqrt(LT) * 회전가중치
물류 리스크일 = max(0, 접근성 + (실측지연 R16 | KB residual))
총 안전재고 = 통계 안전재고 + 물류 버퍼개
추천 ROP = D_eff * LT + 총 안전재고
발주 요일·주기·Q = 선택 패턴 또는 CAPA 자동 추천
  Q ≈ D_eff × cycle_days
CAPA 1~2 이고 상한 초과 시:
  ROP = MaxCap, 표시 SS = max(0, MaxCap − D_eff×LT)   # 항등 유지
  Q = min(Q, MaxCap)
  → 다회 소량 발주 강화
# 표준(비교 기준) ROP/SS는 행사·경쟁 미반영 D 기준 — 보정은 추천 측에만 반영
```

비교 표 기준선:

- **표준 SS** = `max(0, standard_rop − D×LT)` (user `standard_rop` 또는 모형 기본 ROP와 항등)
- **표준 Q** = `D × std_cycle` (자동: 주 1회 7일, 고정 패턴: 선택 cycle) — LT 일수 아님

지도 API 키 없음/실패 시 **행정동 경로 fallback** (evaluate 200 유지 + guidance).

## 3. Output (`app/pipeline/output`)

- 한 줄 recommendation (**LT 입력 유지** · 레버: ROP · SS · Q · cycle · SL)  
- 매장 요약 (서비스 레벨·발주 요일 포함)  
- 비교 표 (입력 LT · SL/Z · 안전재고 · Q · 발주 요일·주기 · ROP)  
- 근거 블록 4개 (물류리스크→버퍼 / 수요·운영레버 / geo / CAPA)  
- guidance 배열  

## API

| Method | Path |
|--------|------|
| `GET` | `/api/health` |
| `GET` | `/api/template` |
| `GET` | `/api/regions/sido` · `/api/regions/sigungu` · `/api/regions/dong` |
| `GET` | `/api/places/search` (점포·주소 자동완성, Kakao) |
| `POST` | `/api/evaluate` |
| `POST` | `/api/simulate` (경쟁·LT·ROP 충격 시나리오) |

정확한 주소 UX: 시·도 → 시·군·구 → 읍·면·동(카카오 제안) 선택 후 점포명/도로명 일부 입력 → 콤보에서 공식 점포 선택 → `store_address`에 도로명 주소 확정.

원 지시(역사 문서, Adjusted LT 서사 포함): `2026-07-14-New-Service-Flow.md` — **구현 SSOT는 본 파일 + `docs/architecture.md`**.

## 4. 산출 근거 (국면 XI)

공식 항별 **문헌·기관 출처 · engineering assumption** 매핑:

- 패키지 인덱스: [`docs/evidence/README.md`](../evidence/README.md)
- 항별 매트릭스 SSOT: [`docs/evidence/evidence-matrix.md`](../evidence/evidence-matrix.md)
- 시연 스코프(매장2·품목2): [`docs/evidence/demo-scope.md`](../evidence/demo-scope.md)

3층: **L1** 표준 재고이론 · **L2** King/APICS·ASCM·Huff 등 · **L3** 본 서비스 명시 proxy.
