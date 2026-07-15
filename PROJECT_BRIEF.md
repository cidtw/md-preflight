# Project Brief — 매장 특화 ROP 재조정 (2026-07-14+)

> v1 프로모션 사전검수: `archive/v1-md-preflight/` · 태그 `archive/v1-md-preflight`

## 한 줄

매장 유형·규모·객단가·행정동·상권·접근성과 품목 일평균 소진량을 입력하면,  
사전 가중치와 지식 베이스 매칭으로 **ROP·안전재고·발주 레버** 와 근거 리포트를 제공한다.  
**Lead Time은 품목 입력으로 고정**하고, 접근성·KB 물류 리스크는 **버퍼 재고(개)** 로 전환한다.

## 파이프라인

```
input (template) → analyze (scores + KB + formulas) → output (comparison report)
```

## 핵심 공식

1. LT_input = 품목 표준/계약 LT (미입력 시 규모 밴드→채널 기본값; 출력에서 변동 추천 없음)  
2. risk_days = max(0, 접근성 + KB 상권·행정동 리스크) · buffer = D × risk_days  
3. SS_stat = Z × D × sqrt(LT × vol/5) × 회전가중 · SS = SS_stat + buffer  
4. ROP = D × LT + SS (CAPA 캡 시 표시 SS를 유효값으로 재계산해 항등 유지)  
5. CAPA 협소 시 상한 캡 + 다회 소량 발주 제안 · 조정 레버 = ROP/SS/Q/요일/서비스 레벨  

## 비목표

- v1 Excel 3파일 프로모션 검수  
- 실시간 LLM 필수 경로 (현재 KB는 결정론 매처)
- 관측 수요 σ 기반 교과서 SS (현재는 휴리스틱 인덱스; UI에 명시)

## 문서

- **정본 파이프라인**: `docs/redesign/pipeline.md`  
- 플로우: `2026-07-14-New-Service-Flow.md`  
- 재설계 판: `docs/redesign/`  

