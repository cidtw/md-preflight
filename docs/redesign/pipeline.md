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
| `trade_area` | 상권 유형 |
| `accessibility` | 대로변 / 이면 / 건물 내 |
| `daily_demand` | 일평균 소진량 |
| `standard_lead_time_days` | (선택) 사내 표준 LT |
| `standard_rop` | (선택) 사내/업계 표준 ROP |

불일치 안내:

- 유형 vs 규모 상이 → **규모** 기준 연산 + guidance  
- 유형 vs 객단가 상이 → **객단가** 기준 연산 + guidance  

## 2. Analyze (`app/pipeline/analyze`)

1. **스코어링 테이블** (`scoring.py`) — CAPA, 수요집중, 회전가중, 공급난이도, 수요변동, 접근성 ΔLT  
2. **(선택) Google Maps 보강** (`geo_enrichment.py`) — 상세 주소 geocode + Nearby POI → `foot_traffic_index`  
3. **KB 매칭** (`knowledge_base.py`) — 행정동+품목+상권 시드 + 유동지수 기반 물류지연·Z계수·서술  
4. **공식** (`engine.py`)

```
foot_traffic_index = clamp( Σ w(category)*exp(-d/250) / 4 , 0, 1)
Z = Z_base + 0.35 * foot_traffic_index
추천 LT = 표준 LT + 접근성 가산 + KB 물류 지연
매장 안전재고 = Z * sqrt(추천LT * 수요변동성) * 회전가중치
추천 ROP = 일평균소진 * 추천LT + 매장 안전재고
CAPA 1~2 이고 상한 초과 시 ROP = MaxCap, 다회 소량 발주 제안
```

지도 API 키 없음/실패 시 **행정동 경로 fallback** (evaluate 200 유지 + guidance).

## 3. Output (`app/pipeline/output`)

- 한 줄 recommendation  
- 매장 요약  
- 표준 vs 추천 비교 표  
- 근거 3블록 (LT / 수요·안전재고 / CAPA)  
- guidance 배열  

## API

| Method | Path |
|--------|------|
| `GET` | `/api/health` |
| `GET` | `/api/template` |
| `POST` | `/api/evaluate` |

지시 원문: `2026-07-14-New-Service-Flow.md`
