# 공식 항 ↔ 코드 ↔ 출처 매트릭스 (SSOT)

> 구현 계약: `docs/redesign/pipeline.md`  
> 근거 등급: **L1** 표준이론 · **L2** 문헌/기관 수치 · **L3** 본 서비스 명시 assumption  
> 코드 경로는 `app/pipeline/` 기준.

---

## 0. 전체 식 (한 장)

| 기호 | 정의 | 코드 | 층 |
|------|------|------|-----|
| \(D\) | 일평균 소진 (입력) | `daily_demand` | 입력 |
| \(m_e\) | 행사 수요 배수 ≥1 | `event_demand_multiplier` | L3 (형태 L2) |
| \(m_c\) | 경쟁 수요 계수 ≤1 | `competition_demand_factor` | L3 (형태 L1 Huff) |
| \(D_{eff}\) | \(D \cdot m_e \cdot m_c\) | `effective_daily_demand` | 합성 |
| \(L\) | 품목 표준/계약 LT (일) | `standard_lead_time_days` **고정** | L1 (역할) · L3 (디폴트값) |
| \(Z_{pol}\) | 정책 CSL → z | `SERVICE_LEVEL_Z` | **L2 King** |
| \(Z\) | \(Z_{pol}\) + 맥락 | `safety_z_factor` | L2+L3 |
| \(v\) | 수요변동 점수 1–5 | `demand_volatility` | L3 proxy for σ |
| \(\tilde\sigma\) | \(D_{eff}\sqrt{L\cdot v/5}\) 형태의 스케일 | `store_safety_stock` 내부 | L1 형태 · L3 σ |
| \(w_t\) | 회전(객단가) 가중 | `turnover_weight` | L3 |
| \(SS_{stat}\) | proxy: \(Z \cdot D_{eff} \cdot \sqrt{L\cdot v/5} \cdot w_t\) · **R16**: \(Z \cdot \sigma_D \cdot \sqrt{L} \cdot w_t\) | `statistical_safety_stock` · `ss_mode` | L1+L3 / R16 |
| \(r\) | proxy: access+KB · **R16**: access+실측 지연 | `logistics_risk_days` · `logistics_delay_mode` | L3 / R16 |
| \(B\) | \(D_{eff}\cdot r\) | `logistics_buffer_units` | L1(LT 변동 버퍼 개념)+L3 |
| \(SS\) | \(SS_{stat}+B\) (CAPA 시 재계산) | `store_safety_stock` | 합성 |
| \(ROP\) | \(D_{eff}\cdot L + SS\) | `recommended_rop` | **L1** |
| \(Q\) | \(D_{eff}\cdot cycle\) (CAPA clamp) | `suggested_order_qty` | L2 근사 |
| MaxCap | \(D_{eff}(L+\text{cover})\) | `max_rop_for_capa` | L3 |

**항등식 (항상 유지)**: 표시 ROP = \(D_{eff}\cdot L\) + 표시 SS  
(CAPA 캡 시 SS를 역산 — `engine.py` · 테스트 `test_pipeline.py`)

---

## 1. ROP 골격

| 항목 | 내용 |
|------|------|
| **식** | \( ROP = D_{eff} \times L + SS \) |
| **코드** | `engine.py` → `raw_rop` / `recommended_rop` |
| **L1** | Continuous review: reorder when inventory position hits LTD + SS |
| **L2** | Netstock/NetSuite/inFlow 등 동일 식; King은 SS 쪽 상세 |
| **L3** | \(D\) 대신 옵션 보정 \(D_{eff}\); 표준 비교열은 행사·경쟁 미반영 \(D\) |
| **시연 한 줄** | “발주 시점은 리드타임 동안 팔릴 양 + 여유 재고” |
| **한계** | 확정적 D·L 가정; 확률적 수요는 SS로만 흡수 |

---

## 2. Lead Time \(L\) (고정 입력)

| 항목 | 내용 |
|------|------|
| **식** | \(L = L_{input}\) 또는 채널 디폴트; \(\Delta L_{rec}=0\) |
| **코드** | `engine.py` `fixed_lt` · `lead_time_fixed=True` · `domain_catalog.DEFAULT_STANDARD_LT` |
| **L1** | LTD = D·L. L은 공급 계약 파라미터; “추천으로 L을 늘려라”는 운영 레버가 아님 (계약 주체 ≠ 점포 발주) |
| **L2** | King: lead time variability는 **SS 항**으로 처리. ASCM 동일 정신 |
| **L3 디폴트** | convenience 1.5 / super 2.0 / ssm 2.5 / hyper 3.0 — 국내 일배~주간 납품 **관례 디폴트** (입력 우선) |
| **시연** | 비교표 “배송 리드타임 · 변경 없음” |
| **한계** | 공개 채널별 공식 LT 통계 부재 → 디폴트는 L3 |

---

## 3. 정책 Z (\(Z_{pol}\))

| 항목 | 내용 |
|------|------|
| **식** | CSL 90/95/99% → z = 1.28 / 1.65 / 2.33 |
| **코드** | `domain_catalog.SERVICE_LEVEL_Z` · `knowledge_base.match_knowledge` |
| **L1** | 정규 근사 하 cycle service level → standard normal quantile |
| **L2** | **King APICS 2011 Fig.2** 표와 일치 · ASCM CSL 논의 |
| **L3** | 기본 선택 `sl_95` (업계 균형점 관례 90–98% 구간 중앙) |
| **시연** | “95%면 재보충 사이클 100번 중 약 5번은 여유재고로도 부족할 수 있음 (King)” |
| **한계** | Fill rate ≠ CSL. 전문 토글에 구분 표기 권장 |

---

## 4. 맥락 Z 가산 (\(Z = Z_{pol} + Z_{ctx}\))

| 항목 | 내용 |
|------|------|
| **식** | \( Z_{ctx} = (v/5)\cdot 0.45 + \text{product_boost} + u\cdot 0.15 + 0.35\cdot FTI \) |
| **코드** | `knowledge_base.match_knowledge` · `FOOT_TRAFFIC_Z_BOOST=0.35` |
| **L1** | 품목·입지마다 목표 보호 수준을 다르게 (King: Z를 제품군별 독립 설정 권고) |
| **L2** | “전략·마진·변동에 따라 Z 차등” — King 본문 |
| **L3** | 가산 계수·product 키워드 부스트·hash unit — **캘리브레이션 아님** |
| **시연** | “정책 바닥 Z 위에 매장 맥락을 올린 것; 바닥은 문헌 표, 가산은 proxy” |
| **한계** | 가산이 CSL 해석을 흐릴 수 있음 → 비교표에 policy Z vs context Z 분리 표시 (현행 UI) |

---

## 5. 통계 안전재고 \(SS_{stat}\)

| 항목 | 내용 |
|------|------|
| **식** | \( SS_{stat} = Z \cdot D_{eff} \cdot \sqrt{L \cdot (v/5)} \cdot w_t \) |
| **코드** | `knowledge_base.store_safety_stock` |
| **L1 형태** | \( SS = Z \cdot \sigma_{LTD} \), \(\sigma_{LTD} \propto \sigma_D \sqrt{L}\) (King/ASCM/√L 통계) |
| **L2** | Z·√L 구조는 문헌 정합 |
| **L3 σ proxy** | 실측 \(\sigma_D\) 대신 \( D_{eff} \sqrt{v/5} \)  
  해석: 일수요 스케일의 **상대 변동 계수(CV) proxy**. v=5 → √1=1·D 스케일, v=1 → √0.2≈0.45·D |
| **L3 \(w_t\)** | 객단가 밴드 0.7–1.5 — 고단가·저회전 SKU는 보수적(가중↑ 아님: 저티켓 1.5=고회전 압력으로 SS↑) |
| **시연 walk-through** | 예: D=12, L=2, v=4, Z≈2.0, w=1.5 → √(2·0.8)=√1.6≈1.26 → SS_stat≈2·12·1.26·1.5≈45 |
| **한계** | POS 표준편차 미사용. 고도화 시 \(\sigma_D\) 직접 대입하면 L3 제거 가능 |

---

## 6. 물류 버퍼 \(B = D_{eff} \times r\)

| 항목 | 내용 |
|------|------|
| **식** | \( r = \max(0,\; \delta_{access} + d_{KB}) \), \( B = D_{eff}\cdot r \) |
| **코드** | `scoring._ACCESS_LT_DELTA` · `knowledge_base.logistics_delay` · `engine.logistics_buffer` |
| **L1** | King: LT 변동 보호 \( SS_{LT} = Z \sigma_{LT} D \). 평균 지연 \(\mathbb{E}[\Delta L]\) 이 있으면 사실상 LTD 증가 ≈ \(D\cdot\mathbb{E}[\Delta L]\) |
| **L2** | “지연은 재고 일수로 환산”은 실무 days-of-supply 사고와 동형 |
| **L3 \(\delta_{access}\)** | main_road −0.5 · alley +0.5 · indoor +1.0 (일) — 하역·진입 난이도 **엔지니어링 일수** |
| **L3 \(d_{KB}\)** | `supply_difficulty*0.08 + hash·0.45` — 상권 공급난 + **결정론 residual (확률 아님)** |
| **시연** | “계약 LT는 그대로 두고, 골목·건물 내 지연 가능성을 **여유 개수**로 환산” |
| **한계** | hash 항은 객관 자료 아님 → 시연 시 **“재현용 시드, 캘리브레이션 아님”** 필수. 축소 스코프에서는 동일 매장 고정으로 이슈 완화 |

---

## 7. 수요 변동 점수 \(v\) · 상권 테이블

| trade_area | supply_difficulty | demand_volatility | 정성 근거 (L3) |
|------------|-------------------|-------------------|----------------|
| office | 3 | 4 | 주중 피크·점심/퇴근 집중 |
| residential | 2 | 2 | 비교적 평탄·저녁/주말 |
| campus | 3 | 5 | 학기/방학 이산 점프 |
| suburban | 1 | 3 | 차량 유입, 공급 상대 여유 |
| tourist | 5 | 5 | 시즌·휴일 극단 |

| 항목 | 내용 |
|------|------|
| **코드** | `scoring._TRADE_SCORES` |
| **L1** | 수요 이질성·비정상성이 클수록 더 큰 σ / SS (King·OR 문헌) |
| **L2** | 상권 유형별 시계열 CV 공개 벤치마크는 희소 → **정성 ordinal scale** |
| **L3** | 1–5 ordinal. √(v/5)로 [0.45,1] 스케일 |
| **시연** | “순서는 문헌·현장 합의(관광>캠퍼스 변동), 간격은 선형 assumption” |

---

## 8. CAPA · 규모 · MaxCap

| size | capa | demand_conc | 의미 |
|------|------|-------------|------|
| cv_xs/s | 1 | 5 | 초협소 · 고압 |
| cv_m/l | 2 | 4 | 협소 |
| sm | 3 | 3 | 중 |
| ssm | 4 | 2 | 여유 |
| hyper | 5 | 1 | 여유 |

| cover_days (capa→) | 1:0.6 · 2:1.0 · 3:2.0 · 4:3.5 · 5:5.0 |
| **MaxCap** | \( D_{eff}(L + cover) \) |
| **코드** | `scoring.max_rop_for_capa` · CAPA≤2 시 강제 |
| **L1** | 용량 제약 하 재고 상한; 소량다빈도 정책으로 대체 |
| **L3** | cover_days 수치 — 내부 설계 |
| **시연** | “이론 ROP가 창고를 넘으면 상한 + 자주 발주 (현장 제약 우선)” |

---

## 9. 발주 요일 · Q

| 항목 | 내용 |
|------|------|
| **식** | \( Q \approx D_{eff} \times R \), R∈{1, 2.33, 3.5, 7,…} |
| **코드** | `ORDER_PATTERN_META` · `suggest_order_policy` |
| **L2** | Periodic review cycle stock ≈ D·R |
| **L3 auto** | CAPA↓ 또는 집중↑ → 고빈도 요일 패턴 |
| **비목표** | 완전 EOQ (S,H 미입력) |

---

## 10. Geo · 행사 · 경쟁

### 10.1 Foot traffic index (구조)

| 항목 | 내용 |
|------|------|
| **식** | soft_sat( Σ w·e^{−d/250}·0.5^{rank} ), soft_sat(x)=x/(x+2.4) |
| **코드** | `geo_enrichment.py` |
| **L2 형태** | 거리 감쇠·최근접 우선 — 공간상호작용/Huff 계열 |
| **L3** | 250m, half-sat 2.4, 카테고리 가중 — engineering |

### 10.2 일시 유동

| 항목 | 내용 |
|------|------|
| **식** | uplift soft_sat; \( m_e = 1 + 0.35\cdot uplift \) (max +35%) |
| **코드** | `event_foot_traffic.py` · r=200m |
| **L2** | 대형 집객 시설 근접 → 일시 수요 충격 (도시·이벤트 소매 일반) |
| **L3** | 0.35 cap · 키워드 시설 프록시 (실시간 일정 없음) |
| **정직 표기** | “행사 캘린더 없음 → 시설 근접 proxy” |

### 10.3 경쟁 포화

| 항목 | 내용 |
|------|------|
| **식** | intensity soft_sat; \( m_c = 1 - 0.40\cdot intensity \) |
| **코드** | `competition_saturation.py` · tier weights 1.0/0.85/0.40 |
| **L1** | Huff: 경쟁 점포 pull이 점유율 분산 |
| **L3** | −40% cap · decay·반경 테이블 |
| **시연** | “형태는 Huff, 계수는 상한 가드레일” |

---

## 11. 표준 대비 기준선 (비교 표)

| 열 | 정의 | 근거 |
|----|------|------|
| 표준 ROP | 입력 `standard_rop` 또는 \(D\cdot L + base\_frac\cdot D\cdot L\) | 사내/채널 평균 가정 |
| 표준 SS | \(\max(0, ROP_{std} - D\cdot L)\) | ROP 항등 |
| 표준 Q | \(D \times R_{std}\) (자동 시 7일) | 주 1회 관례 디폴트 |
| 추천 열 | \(D_{eff}\), 맥락 Z, 버퍼 포함 | 본 모형 |

`DEFAULT_BASE_SAFETY_FRAC` (0.25–0.55): King이 비판한 “사이클의 %” 휴리스틱과 **형태는 유사**하나, **표준 열 기본값**에만 쓰고 추천 SS는 통계+버퍼 경로. 시연 시 구분 필수.

---

## 12. “객관 자료로 답 가능한 것 / 아직 proxy인 것”

### 단단함 (시연에서 먼저)

1. ROP = LTD + SS (L1)  
2. Z 표 90/95/99 = 1.28/1.65/2.33 (King/APICS, ASCM)  
3. SS ∝ Z · √L · (수요 스케일) (L1+L2)  
4. LT 고정 · 지연은 버퍼 (L1 정신)  
5. 경쟁 거리 감쇠 형태 (Huff L1)  
6. CAPA 시 항등 유지 · 소량다빈도 (제약 합리)

### 명시 proxy (숨기지 말 것)

1. vol 1–5 → σ  
2. 접근성 일수 테이블  
3. hash logistics residual  
4. FTI/행사/경쟁 soft-sat 계수  
5. cover_days · DEFAULT_LT · base_frac  
6. 객단가 turnover 가중

### 축소 스코프로 완화

- 매장 2 · 품목 2 고정 → hash/테이블을 “이 케이스의 고정 파라미터”로 제시  
- walk-through 한 장에 L1→L2→L3 숫자 전개 (`demo-scope.md`)

---

## 13. 코드 참조 인덱스

| 개념 | 파일 · 심볼 |
|------|-------------|
| Z 표 | `domain_catalog.SERVICE_LEVEL_Z` |
| 채널 기본 LT | `DEFAULT_STANDARD_LT` |
| 통계 SS | `knowledge_base.store_safety_stock` |
| Z 맥락 | `match_knowledge` |
| 점수표 | `scoring.score_store` |
| MaxCap | `max_rop_for_capa` |
| 엔진 조립 | `engine.analyze` |
| 계약 문서 | `docs/redesign/pipeline.md` |
