# 파이프라인 계약 — Input → Analyze → Output

```
[클라이언트]
    │  parameters (JSON)
    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. INPUT   │ ──► │ 2. ANALYZE  │ ──► │ 3. OUTPUT   │
│  템플릿 검증 │     │ 가중치 점수  │     │ 한 줄 추천  │
└─────────────┘     └─────────────┘     └─────────────┘
    │                     │                     │
    ▼                     ▼                     ▼
 ValidatedInput      AnalysisResult     RecommendationResult
```

## 1. Input (`app/pipeline/input`)

- **역할**: 공개 템플릿에 맞춰 파라미터 수신·검증  
- **템플릿**: `GET /api/template` — 키·타입·범위·필수 여부  
- **요청**: `POST /api/evaluate` body `{ "parameters": { ... } }`  
- **실패**: 400 + 필드별 메시지 (판정 엔진으로 넘기지 않음)

## 2. Analyze (`app/pipeline/analyze`)

- **역할**: 사전 구성된 기준(criterion) × 가중치로 점수 산출  
- **불변**: 동일 입력 → 동일 점수 (결정론)  
- **스켈레톤**: 플레이스홀더 기준 세트 (`weights.py`) — **실 조사 가중치는 DEFER**  
- **출력**: 총점, 기준별 raw/weighted, 밴드(strong/moderate/weak)

## 3. Output (`app/pipeline/output`)

- **역할**: 분석 결과를 **한 줄 recommendation**으로 고정 포맷 렌더  
- **필드**: `recommendation` (str), `score`, `band`, `details`  
- **확장**: 이후 리포트/체크리스트는 이 스테이지에 모듈 추가

## 오케스트레이션

`app/pipeline/runner.py` → `run(parameters) -> RecommendationResult`  
HTTP는 `app/api/routes.py`에서 runner만 호출 (얇은 어댑터).

## 모듈 추가 가이드

1. 새 **입력 필드** → 템플릿 + input validator  
2. 새 **평가 기준** → `analyze/weights.py` (또는 향후 criteria 패키지)  
3. 새 **출력 형식** → `output/` 렌더러 추가, runner 옵션으로 연결  
4. 스테이지 간 계약(`app/pipeline/types.py`)을 깨지 말 것  
