# Project Brief — Redesign Skeleton (2026-07-14+)

> v1 (프로모션 사전검수)는 `archive/v1-md-preflight/` 및 git 태그 `archive/v1-md-preflight`에 동결.

## 한 줄

파라미터 템플릿으로 값을 받고, 사전 구성된 평가 가중치로 분석한 뒤, **한 줄 recommendation**을 내는 모듈형 파이프라인.

## 방향성

1. 좁은 스코프 · 논리와 근거가 명확  
2. 열린 입력 (특정 파라미터) → 조사 기반 가중치 → 한 줄 추천  
3. 간결 구조 · 환경 무관 동일 경험  
4. 블록·모듈형으로 이후 기능 추가  

## 파이프라인

```
input (template) → analyze (weights) → output (recommendation)
```

| 단계 | 코드 | 역할 |
|------|------|------|
| Input | `app/pipeline/input` | 템플릿 검증 |
| Analyze | `app/pipeline/analyze` | 결정론 가중 점수 |
| Output | `app/pipeline/output` | 한 줄 recommendation |

## 비목표 (현재)

- Excel/CSV 3파일 프로모션 검수 (v1)  
- Clerk / Neon / 멀티 LLM  
- 대형 SPA  

## 다음

`docs/redesign/board.md` — 도메인·가중치 조사 후 스켈레톤 교체.
