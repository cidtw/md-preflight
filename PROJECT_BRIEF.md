# Project Brief — 매장 특화 ROP 재조정 (2026-07-14+)

> v1 프로모션 사전검수: `archive/v1-md-preflight/` · 태그 `archive/v1-md-preflight`

## 한 줄

매장 유형·규모·객단가·행정동·상권·접근성과 품목 일평균 소진량을 입력하면,  
사전 가중치와 지식 베이스 매칭으로 **추천 Lead Time / ROP** 와 근거 리포트를 제공한다.

## 파이프라인

```
input (template) → analyze (scores + KB + formulas) → output (comparison report)
```

## 핵심 공식

1. 추천 LT = 표준 LT + 접근성 가산 + KB 물류 지연  
2. 매장 안전재고 = Z * sqrt(추천LT * 수요변동성) * 회전가중치  
3. 추천 ROP = 일평균소진 * 추천LT + 매장 안전재고  
4. CAPA 협소 시 상한 캡 + 다회 소량 발주 제안  

## 비목표

- v1 Excel 3파일 프로모션 검수  
- 실시간 LLM 필수 경로 (현재 KB는 결정론 매처)

## 문서

- 플로우: `2026-07-14-New-Service-Flow.md`  
- 재설계 판: `docs/redesign/`  
