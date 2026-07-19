# 산출 근거 패키지 (Evidence Package)

> **목적**: 시연·평가 시 *“이 ROP/LT/SS 숫자의 근거가 무엇이냐?”* 에 대해  
> **표준 이론 → 1차 출처 → 본 서비스 설계 선택** 3층으로 답한다.  
> **튜터 방향**: 품목·매장 수를 줄여도 되므로 **논리 완결성**을 우선한다.  
> **작성**: 2026-07-19 · 브랜치 `pivot/project-direction`

## 한 줄

```
ROP = D_eff × LT + SS
SS  = 통계 안전재고(Z, √LT, 변동 proxy) + 물류 버퍼(D × 리스크일)
LT  = 품목 계약/표준 입력 (출력에서 재조정하지 않음)
```

공식 **골격**은 연속검토(continuous review) 재고이론의 표준형이다.  
시연 리스크는 골격이 아니라 **계수·가중치의 출처 표기**다. 본 폴더가 그 표기다.

## 3층 답변 구조 (시연 스크립트)

| 층 | 이름 | 답하는 내용 | 예 |
|----|------|-------------|-----|
| **L1 Primary** | 표준 이론 | 왜 이 *형태*의 식인가 | ROP = LTD + SS · SS = z·σ_LTD (King/APICS, ASCM) |
| **L2 Secondary** | 1차 출처 범위 | Z·√L·채널 LT 등이 문헌/기관에서 어디에 있는가 | CSL 90/95/99 → z≈1.28/1.65/2.33 |
| **L3 Tertiary** | 서비스 설계 선택 | POS σ 없을 때 *무엇을 proxy로 썼는지* · 명시 assumption | vol_norm=score/5 · 접근성 일수 테이블 |

시연 한 문장:

> “재주문점은 리드타임 수요에 안전재고를 더한 연속검토 표준식입니다.  
> 서비스 레벨 Z는 정규 근사 표(King CSCP / APICS)를 쓰고,  
> 매장 변동·접근성 계수는 문헌 범위 안의 **명시적 engineering proxy**입니다.  
> 상세 매핑은 `docs/evidence/` 입니다.”

## 문서 목록

| 파일 | 내용 |
|------|------|
| [`literature-sources.md`](./literature-sources.md) | 문헌·기관·실무 1차/2차 출처 목록 |
| [`evidence-matrix.md`](./evidence-matrix.md) | **공식 항 ↔ 코드 ↔ 출처 ↔ 가정** 매트릭스 (SSOT) |
| [`demo-scope.md`](./demo-scope.md) | 스코프 축소 시연 시나리오 (매장 2 · 품목 2) |
| [`parameter-ranges.md`](./parameter-ranges.md) | 우리 계수 vs 문헌 관례 범위 대조 |

## 시연 매장 선택

- **가능**: 위저드에서 「정확한 위치」→ 시·군·구·동 → Kakao **점포 검색으로 특정 매장 선택**  
- **시연 보장**: `app/pipeline/verified_demo_stores.py` 의 **검증 프로필 1–2곳**만 (숫자 walkthrough 고정)  
- **탐색 유지**: 기존 행정동·더미 시나리오·지도 API 샘플 주소 (서사 본체 아님)

## 관련 코드·계약

| 경로 | 역할 |
|------|------|
| `docs/redesign/pipeline.md` | 파이프라인 공식 계약 (구현 SSOT) |
| `app/pipeline/analyze/engine.py` | 연산 오케스트레이션 |
| `app/pipeline/analyze/knowledge_base.py` | Z 맥락 · 통계 SS |
| `app/pipeline/analyze/scoring.py` | CAPA·상권·접근성 점수표 |
| `app/pipeline/domain_catalog.py` | Z 표 · 채널 기본 LT |

## R16 — 실측 입력으로 L3 축소

| 선택 입력 | 효과 | `calc` 플래그 |
|-----------|------|----------------|
| `demand_sigma_daily` | \(SS = Z \sigma_D \sqrt{LT} w_t\) (King 형태) · vol proxy OFF | `ss_mode=measured_sigma` |
| `measured_logistics_delay_days` | KB hash residual 대체 · risk = 접근성 + 실측 | `logistics_delay_mode=measured_delay` |

미입력 시 기존 L3 proxy. 전문 토글 **산출 근거 층** 카드에 모드가 반영된다.

## 한계 (정직하게)

1. **기본 경로**는 POS σ 없음 → vol 점수 proxy (R16으로 교체 가능).  
2. **계약 LT**는 입력 고정; 지연은 버퍼 재고로 분리.  
3. **행정동 hash residual** → 재현 시드 (캘리브 아님) · R16 실측 지연으로 대체 가능.  
4. **경쟁·행사 soft-sat** → Huff 형태 · 계수는 engineering cap.

한계를 숨기지 않는 것이 튜터 피드백(객관 근거) 대응의 일부다.
