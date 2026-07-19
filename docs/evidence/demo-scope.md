# 시연 스코프 축소 — 논리 완결 시나리오

> 튜터: *품목·분석 매장 수를 줄여도 되니 논리적 완벽을 기하라.*  
> **실측 채움**: 2026-07-19 · `app.pipeline.runner.run` · template **v1.6.0**  
> (행정동 경로 · precise location OFF · 행사/경쟁 OFF)

---

## 1. 스코프

| 축 | 개수 | 선택 |
|----|------|------|
| 매장 | **2** | A 오피스 편의점(건물 내) · B 주거 밀착 슈퍼(대로변) |
| 품목 | **2** | ① 냉장 간편식(고변동) · ② 상온 라면/스낵(저변동) |
| 조합 | **최대 2 런** | **A×① 필수** · (선택) B×② 대조 |

### 시연 UI 경로 (매장 선택)

| 경로 | 용도 |
|------|------|
| **검증 매장 (1–2곳)** | 시연 본체 · `VERIFIED_DEMO_STORES` · `GET /api/demo/verified-stores` |
| **탐색·더미 / 지도 API** | 기존 행정동·Kakao 점포 검색 유지 · 서사 본체 아님 |

특정 **실매장 점포명**을 Kakao로 고를 수는 있으나, 그 경로에는 POS 검증 수요·ROP 체인이 없음.  
시연 숫자는 **검증 프로필 A/B**만 보장한다 (`use_precise_location=false` 행정동 경로).

---

## 2. 시나리오 A — 필수 워크스루 (실측)

### 입력 (고정)

| 필드 | 값 |
|------|-----|
| product_name | 냉장 간편식 도시락 |
| store_type / size | convenience / **cv_s** |
| avg_ticket | t_le_8k |
| location_dong | 서울시 강남구 역삼1동 |
| trade_area | office |
| accessibility | indoor |
| daily_demand D | **12** |
| standard_lead_time_days L | **2** |
| service_level | sl_95 → **Z_pol = 1.65** |
| order_day_pattern | auto |
| use_precise_location | false |

### 중간 점수 (실측)

| 항목 | 값 |
|------|-----|
| capa_score | **1** (협소) |
| demand_concentration | 5 |
| turnover_weight | 1.5 |
| demand_volatility | 4 (office) |
| accessibility_lt_delta | **+1.0** 일 (indoor) |
| KB logistics_delay | **0.30** 일 (proxy_kb) |
| logistics_risk_days | **1.30** (= 1.0 + 0.30) |
| Z 맥락 (최종) | **2.38** (정책 1.65 + 맥락) |
| ss_mode | proxy_vol |
| logistics_delay_mode | proxy_kb |

### 산출 체인 (실측 숫자)

```
① L1  LTD = D × L = 12 × 2 = 24
② L2  Z_pol(95%) = 1.65  ← King/APICS
③     Z_ctx = 2.38 (비교표: 정책 → 매장 반영)
④ L3  SS_stat (캡 전) = 54.19
         = Z×D×√(LT×vol/5)×turnover
         = 2.38×12×√(2×0.8)×1.5
⑤ L3  buffer = D × risk_days = 12 × 1.30 = 15.60
⑥     raw SS = 54.19 + 15.60 = 69.79
      raw ROP = 24 + 69.79 = 93.79
⑦ CAPA MaxCap = D×(L+0.6) = 12×2.6 = 31.2
      → capa_capped: ROP = 31.2
      → 표시 SS = 31.2 − 24 = 7.2  (항등 유지)
⑧ 발주: 월·수·금 (cycle 2.33일) · Q raw 28 → Q=28 (≤ MaxCap 31.2)
⑨ 표준 ROP (base_frac 경로) = 30.0 · ΔROP = +1.2
```

### 한눈에 표 (라이브 UI와 동일)

| 지표 | 값 |
|------|-----|
| **추천 ROP** | **31.2개** (CAPA 상한) |
| raw ROP (이론) | 93.79개 |
| 표준 ROP | 30.0개 |
| 표시 SS | **7.2개** |
| 통계 SS (캡 전) | 54.19개 |
| 물류 버퍼 | 15.6개 |
| Q | **28개** |
| 발주 요일 | **월·수·금** (≈2.33일) |
| LT | **2일 고정** |

### 추천 한 줄 (plain, 실측)

> [냉장 간편식 도시락] 재고가 약 **31개** 아래로 떨어지기 전에 발주해 주세요.  
> 매장·창고 공간이 넉넉하지 않아, **월·수·금**에 한 번에 약 **28개**씩 자주 나눠 넣는 운영을 권합니다.  
> 배송 일정은 지금처럼 **2일** 그대로 두면 됩니다.

### 질의 “근거?” 답 (이 숫자로)

1. 식의 형태 → ROP = LTD + SS (L1)  
2. 1.65 → King Fig.2 CSL 95% (L2)  
3. √L · Z·σ 골격 → ASCM/King (L2)  
4. 12, 2 → **이 데모 입력**  
5. 54.19 / 15.6 / risk 1.3 → L3 proxy (vol·hash·접근성) — 전문 토글 **산출 근거 층**  
6. **31.2** → CAPA 물리 상한 (이론 93.79를 못 쌓음 → 다회 소량)

### R16 옵션 (같은 입력에 추가 시)

| 입력 | 효과 |
|------|------|
| `demand_sigma_daily` | SS_stat = Z×σ×√LT×turnover · `ss_mode=measured_sigma` |
| `measured_logistics_delay_days` | KB residual 대체 · risk = access + 실측 · `logistics_delay_mode=measured_delay` |

예: σ=3.0 → SS_stat **15.15** (proxy 54.19 대비 축소).  
예: 실측 지연 0.5일 → risk **1.5**, buffer **18.0**.

---

## 3. 시나리오 B — 대조 (실측 · 2026-07-19)

> 같은 정책 SL=95% · LT=2일이어도 매장·상권·접근·품목이 바뀌면 ROP 구조가 달라진다.

### 입력

| 필드 | 값 |
|------|-----|
| product_name | 상온 라면 |
| store_type / size | supermarket / **sm** |
| avg_ticket | t_8k_15k |
| location_dong | 서울시 강남구 역삼1동 (A와 동일 행정동) |
| trade_area | **residential** |
| accessibility | **main_road** |
| daily_demand D | **8** |
| L / SL / pattern | 2 / sl_95 / auto |

### 중간 점수 (실측)

| 항목 | B | A (참고) |
|------|---|----------|
| capa | **3** | 1 |
| demand_vol | **2** | 4 |
| access delta | **−0.5** | +1.0 |
| KB residual | 0.25 | 0.30 |
| risk_days | **0.00** (max(0,−0.5+0.25)) | 1.30 |
| Z_pol → Z | 1.65 → **1.96** | 1.65 → 2.38 |
| capa_capped | **false** | true |

### 산출 (실측)

| 지표 | B | A |
|------|---|---|
| LTD | 8×2 = **16** | 24 |
| SS_stat | **21.04** | 54.19 (캡 전) |
| buffer | **0.0** | 15.6 |
| raw / 추천 ROP | **37.04** (캡 없음) | raw 93.79 → **31.2** |
| 표시 SS | **21.04** | **7.2** (캡 후) |
| 표준 ROP | 21.6 · Δ **+15.44** | 30.0 · Δ +1.2 |
| Q | **28** (cycle 3.5) | 28 (cycle 2.33) |
| 발주 요일 | **월·목** | 월·수·금 |

### 추천 한 줄 (plain, 실측)

> [상온 라면] 일반 기준보다 약 **15개** 더 여유 있게 잡았습니다.  
> 재고가 약 **37개** 수준에 가까워지면 발주, **월·목**에 한 번에 약 **28개**.  
> 배송 일정은 **2일** 그대로.

### A vs B 한 줄 서사

| | A 오피스 편의·건물내·냉장 | B 주거 슈퍼·대로·상온 |
|--|---------------------------|------------------------|
| 병목 | **공간(CAPA)** — 이론 SS를 못 쌓음 | **수요 맥락 SS** — 캡 없이 통계 SS 전부 반영 |
| 버퍼 | 지연 리스크 일수 큼 | 대로변으로 risk **0** |
| 운영 | 고빈도(월수금) 소량 | 중빈도(월목) |

---

## 4. 시연에서 하지 말 것

- 5개 이상 매장·품목 나열  
- “hash가 행정동 리스크를 학습했다” 과대 주장  
- CAPA 캡 **전** raw ROP만 보여 주고 표시 ROP와 혼동  
- 표준 열 base_frac 을 통계 SS와 혼동

---

## 5. 재현 명령

```bash
uv run python -c "
from app.pipeline.runner import run
r = run({
  'product_name': '냉장 간편식 도시락',
  'store_type': 'convenience', 'store_size': 'cv_s', 'avg_ticket': 't_le_8k',
  'location_dong': '서울시 강남구 역삼1동',
  'trade_area': 'office', 'accessibility': 'indoor',
  'daily_demand': 12, 'standard_lead_time_days': 2,
  'service_level': 'sl_95', 'order_day_pattern': 'auto',
})
print(r.calc.recommended_rop, r.calc.store_safety_stock, r.calc.capa_capped)
"
```

테스트: `tests/test_pipeline.py::test_scenario_a_measured_walkthrough`
