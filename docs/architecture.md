# MD Preflight 아키텍처 요약 — 리빌드 서비스 (ROP)

> **상태**: Active (국면 VII)  
> **브랜치**: `pivot/project-direction`  
> **버전**: 0.3.2-rop  
> **프로덕션**: https://baljumatch.vercel.app · 제품명 **발주맞춤 · OrderFit**
> **지시 원문**: `2026-07-14-New-Service-Flow.md`  
> **v1 (프로모션 검수)**: 태그 `archive/v1-md-preflight` · `archive/v1-md-preflight/`

---

## 0. 한 줄

매장·상권·접근성 파라미터와 품목 소진량을 받아, **결정론적 점수·지식 베이스 매칭**으로  
**LT 고정 · 안전재고/발주량/주기/ROP 조정**과 **근거 리포트**를 반환한다.

---

## 1. 왜 다시 설계했는가

| v1 문제 | 리빌드 대응 |
|---------|-------------|
| 기능 과다 (10룰·SPA·Clerk/Neon/LLM) | 단일 도메인: 매장 특화 LT/ROP |
| 서비스 근거 빈약 | 사전 가중치 테이블 + KB 근거 3블록 |
| 가벼운 가치 vs 무거운 웹 | 폼 → 로딩 → 리포트 최소 UI |
| 파일 3종 강제 업로드 | 파라미터 템플릿 입력 |

**비목표 (현재)**: Excel 프로모션 검수, 실시간 LLM 필수 경로, ERP/POS 연동.

---

## 2. 전체 구조

```
                    ┌─────────────────────────────────────────────┐
                    │                 app/web                      │
                    │   입력 폼  ──► 로딩  ──► 결과 리포트 UI        │
                    └───────────────────┬─────────────────────────┘
                                        │ JSON
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │              app/api (얇은 HTTP)              │
                    │   GET /api/health · /api/template            │
                    │   POST /api/evaluate                         │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                     app/pipeline/runner.py                        │
│                                                                  │
│   ┌────────────┐    ┌─────────────────────┐    ┌──────────────┐  │
│   │ 1. INPUT   │───►│ 2. ANALYZE (내부)   │───►│ 3. OUTPUT    │  │
│   │ 템플릿검증 │    │ 점수+KB+LT/ROP공식  │    │ 비교·근거    │  │
│   └────────────┘    └─────────────────────┘    └──────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

사용자 체감 흐름은 **1 → (짧은 로딩) → 3**.  
2단계는 서버 내부 전용이며, 동일 입력에 대해 **항상 동일 결과**(결정론).

---

## 3. 3단 파이프라인 상세

### 3.1 Input — `app/pipeline/input/`

| 모듈 | 역할 |
|------|------|
| `template.py` | 공개 템플릿 정의 · 검증 · 불일치 guidance |
| `domain_catalog.py` | 옵션 키·한글 라벨 · 채널 기본 LT/안전재고 비율 |

**필수 파라미터**

| 키 | 의미 |
|----|------|
| `product_name` | 재고 최적화 대상 품목 |
| `store_type` | (무인)편의점 / 일반 슈퍼 / SSM / 대형마트 |
| `store_size` | 연면적 구간 (초소형~하이퍼) |
| `avg_ticket` | 객단가 구간 |
| `location_dong` | 행정동 단위 입지 |
| `trade_area` | 오피스·주거·대학가·교외·관광 |
| `accessibility` | 대로변 / 이면도로 / 건물 내 |
| `daily_demand` | 일평균 소진량(개) |

**선택**: `standard_lead_time_days`, `standard_rop` (미입력 시 채널 기본값·공식 baseline)

**불일치 규칙**

- 유형 vs 규모 상이 → **규모**를 연산 기준으로 강제 + guidance  
- 유형 vs 객단가 상이 → **객단가**를 연산 기준으로 강제 + guidance  

---

### 3.2 Analyze — `app/pipeline/analyze/`

내부 계산 엔진. 사용자에게 중간 UI를 노출하지 않는다.

```
ValidatedInput
      │
      ├─► scoring.score_store()
      │      CAPA · 수요집중 · 회전가중 · 공급난이도 · 수요변동 · 접근성 리스크(일)
      │
      ├─► knowledge_base.match_knowledge()
      │      행정동+품목+상권 시드 → 물류지연일 · 안전계수 Z · 서술 노트
      │
      └─► engine.analyze()
             고정 LT · 표준·추천 ROP/SS · CAPA 상한 · 다회 소량 제안
```

#### 스코어링 축 (사전 설정 테이블)

| 축 | 출처 필드 | 산출 |
|----|-----------|------|
| 물류 창고 CAPA | `store_size` | 1~5점 |
| 수요 집중도 | `store_size` | 1~5점 |
| 회전 가중치 | `avg_ticket` | 0.7 / 1.0 / 1.5 |
| 공급 난이도 | `trade_area` | 1~5 (LT 영향) |
| 수요 변동성 | `trade_area` | 1~5 (ROP 영향) |
| 접근성 리스크(일) | `accessibility` | −0.5 / +0.5 / +1.0 일 → 버퍼 재고 환산 |

#### 지식 베이스 (Agent 형태 · 현재 구현)

- **포트**: `knowledge_base.py` (`match_knowledge`)  
- **현재**: 결정론 해시 시드 + 규칙 테이블 (실 LLM/공공 API 없음)  
- **산출**: `logistics_delay_days`, `safety_z_factor`, 피크/물류/수요 서술  
- **확장 포인트**: 동일 시그니처로 실 Agent·공공 데이터 교체 (board R9–R10)

#### 핵심 공식

> **정본**: [`docs/redesign/pipeline.md`](redesign/pipeline.md) · 아래는 요약.  
> (구) “추천 LT = 표준 + 접근성 + KB” 모델은 **폐기** — LT는 입력 고정, 리스크는 버퍼 재고.

```
LT_input     = 품목 표준/계약 LT (출력 delta=0; 미입력 시 규모 밴드 채널 기본)
Z_policy     = SERVICE_LEVEL_Z[service_level]
Z            = Z_policy + 맥락(변동성·품목·시드·FOOT_TRAFFIC×fti)
risk_days    = max(0, 접근성 + KB 상권·행정동 리스크)
buffer       = D × risk_days
SS_stat      = Z × D × √(LT × vol/5) × 회전 가중치   # 휴리스틱, 실측 σ 아님
SS           = SS_stat + buffer
ROP          = D × LT + SS
Q            = D × cycle_days
CAPA 캡 시   표시 SS = max(0, ROP_cap − D×LT)  # 항등 유지
             Q = min(Q, MaxCap)
```

**CAPA 필터** (CAPA 점수 ≤ 2):

- 물리 상한 `MaxCap` 초과 시 ROP를 상한으로 고정하고 **유효 SS**를 재계산  
- 1회 발주량 `Q`도 `MaxCap`을 넘지 않도록 절사  
- **다회 소량 발주** 제안 문구 활성화  

**표준(baseline) ROP / 비교 표**

- 사용자 `standard_rop` 우선  
- 없으면 `(일평균 × 표준 LT) + 채널 기본 안전재고 비율` (채널 = 규모 밴드 우선)  
- 비교 **표준 SS** = `max(0, standard_rop − D×LT)` (ROP 항등)  
- 비교 **표준 Q** = `D × std_cycle` (자동: 주 1회 7일; 고정 패턴: 선택 cycle)

---

### 3.3 Output — `app/pipeline/output/`

| 모듈 | 역할 |
|------|------|
| `recommendation.py` | 한 줄 추천 · 비교 대시보드 · 근거 4블록 |

**응답 페이로드 (`RecommendationResult`)**

| 필드 | 내용 |
|------|------|
| `recommendation` | 한 줄 요약 (품목 · LT 유지 · ΔROP · SS · Q · cycle · SL) |
| `guidance` | 입력 불일치 안내 (있을 때만) |
| `summary` | 매장·품목·입지 라벨 요약 |
| `comparison` | 표준 vs 추천 (LT 고정 · Z · SS · Q · cycle · ROP) + ROP 안내 |
| `evidence[]` | ① 물류→버퍼 ② 수요·운영레버 ③ geo ④ CAPA 필터 |
| `calc` | 수치 breakdown (점수·KB·공식 중간값) |

**출력 원칙**: 플로우 문서의 예시 문장/수치를 고정 복붙하지 않는다.  
행정동·품목·점수에 따라 **동적 생성**한다.

---

## 4. 계층별 코드 맵

```
app/
├── main.py                 # FastAPI 앱 · 정적 UI 마운트
├── api/
│   ├── routes.py           # /api/* 어댑터 (비즈니스 로직 없음)
│   └── deps.py             # Settings DI
├── core/
│   ├── config.py           # 앱명·버전·CORS
│   └── errors.py           # InputValidationError
├── schemas/
│   └── evaluate.py         # EvaluateRequest/Response
├── pipeline/
│   ├── types.py            # 스테이지 간 계약 (Pydantic)
│   ├── domain_catalog.py   # 카탈로그·기본값
│   ├── runner.py           # input → analyze → output
│   ├── input/template.py
│   ├── analyze/
│   │   ├── scoring.py
│   │   ├── geo_enrichment.py   # Kakao Local POI (optional)
│   │   ├── knowledge_base.py
│   │   └── engine.py
│   └── output/recommendation.py
└── web/
    ├── index.html          # 셸
    ├── app.js              # 폼 빌드 · evaluate · 리포트 렌더
    └── styles.css
```

| 계층 | 책임 | 금지 |
|------|------|------|
| `web` | UX · 템플릿 fetch · 결과 표시 | 점수/공식 로직 |
| `api` | HTTP 검증 에러 매핑 | 도메인 계산 |
| `pipeline` | 전 도메인 결정론 로직 | 프레임워크 종속 최소화 |
| `core` | 설정·에러 타입 | 비즈니스 규칙 |

---

## 5. API 계약

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/health` | `service=rop-adjust`, 버전 |
| `GET` | `/api/template` | 입력 스키마 + 옵션 라벨 |
| `POST` | `/api/evaluate` | `{ "parameters": { ... } }` → 리포트 |
| `GET` | `/` | 최소 웹 UI |

에러: 템플릿 위반 시 **400** + `detail` 메시지.

---

## 6. 런타임 · 배포

| 항목 | 값 |
|------|-----|
| 런타임 | Python 3.11+ (Vercel build: 3.12) |
| 프레임워크 | FastAPI + Pydantic v2 |
| 의존성 | fastapi, pydantic, pydantic-settings, orjson, uvicorn |
| 호스팅 | Vercel (`@vercel/python`, `vercel.json` builds) |
| 프로덕션 URL | https://baljumatch.vercel.app |
| 로컬 | `uv run uvicorn app.main:app --reload --port 8000` |
| 지도 POI | **Kakao Local REST** (`KAKAO_REST_API_KEY`) — 설정: `docs/setup-kakao-local.md` |

**의도적으로 제거된 v1 의존성**: pandas, openpyxl, anthropic, openai, psycopg, PyJWT, Clerk.  
**제거된 지도**: Google Maps (Billing 필수) → Kakao Local로 교체.

---

## 7. 결정론 · 품질 게이트

| 게이트 | 내용 |
|--------|------|
| 동일 입력 | 동일 `calc` · `recommendation` · `evidence` 수치 |
| 테스트 | `tests/test_pipeline.py`, `tests/test_api.py` |
| 검증 명령 | `uv run ruff check app tests` · `basedpyright app` · `pytest` |
| 문서 예시 비고정 | 행정동/품목 기반 동적 문구 테스트 |

---

## 8. v1 대비 경계

| | v1 (archived) | 리빌드 (active) |
|--|---------------|-----------------|
| 도메인 | 프로모션 파일 사전검수 | 매장 특화 LT/ROP |
| 입력 | CSV/XLSX 3프레임 | 파라미터 템플릿 |
| 판정 | 10개 룰 엔진 | 가중치 + 공식 + CAPA |
| 서술 | LLM / fallback | 템플릿형 근거 블록 (+ KB 노트) |
| 영속·인증 | RunStore / Clerk / Neon | 없음 (무상태) |
| 복원 | `git worktree add … archive/v1-md-preflight` | — |

---

## 9. 확장 로드맵 (보드 요약)

| ID | 방향 | 삽입 지점 |
|----|------|-----------|
| R7 | 배포 패리티·Git production branch 정렬 | Vercel 설정 |
| R9 | 실측/공공 데이터 KB | `knowledge_base.match_knowledge` |
| R10 | 실 Agent AI 검색·요약 | 동일 포트, 시그니처 유지 |
| R11 | 품목 마스터·단위 | input catalog |
| R12 | 다회 소량 발주 스케줄 | output + CAPA 분기 |

규칙은 유지한다: **스테이지 계약(`types.py`)을 깨지 말고 모듈로 추가**한다.

---

## 10. 관련 문서

| 문서 | 경로 |
|------|------|
| 본 요약 (정본) | `docs/architecture.md` |
| 서비스 플로우 지시 | `2026-07-14-New-Service-Flow.md` |
| 재설계 방향 | `docs/redesign/direction.md` |
| 파이프라인 계약 | `docs/redesign/pipeline.md` |
| 작업 보드 | `docs/redesign/board.md` |
| 개발 일지 | `docs/dev-journal-2026-07.md` |
| 프로젝트 브리프 | `PROJECT_BRIEF.md` |
| v1 아카이브 | `archive/v1-md-preflight/` · tag `archive/v1-md-preflight` |
| v1 설계 문서 (트리에서 제거) | 태그 경로: `BACKEND_ARCHITECTURE.md`, `docs/architecture-easy.md`, `docs/rule-matrix.md` 등 |

---

*발행: 2026-07-14 · 브랜치 `pivot/project-direction` · 커밋 기준 ROP 서비스 리빌드*
