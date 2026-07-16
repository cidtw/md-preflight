# MD Preflight ROP — 아키텍처 · 파일 기능 · 기술 스택 보고서

| 항목 | 값 |
|------|-----|
| **작성일** | 2026-07-16 |
| **브랜치** | `pivot/project-direction` |
| **기준 커밋** | `d9e53ae` (tip) |
| **앱 버전** | `0.3.5-rop` · 입력 템플릿 `rop-adjust-v1` **1.5.0** |
| **프로덕션** | https://md-preflight.vercel.app |
| **서비스 한 줄** | 매장·상권·(선택) 정확한 위치 파라미터 → 결정론 점수·KB·Kakao 보강 → **LT 고정** 아래 ROP·SS·Q·발주 주기 추천 + 근거 리포트 |

> 본 문서는 **현재 빌드된 활성 코드** 기준이다. v1 프로모션 사전검수는 `archive/v1-md-preflight` 태그로 동결되어 활성 경로에 포함되지 않는다.

---

## 1. 제품 아키텍처 개요

### 1.1 설계 원칙

| 원칙 | 구현 반영 |
|------|-----------|
| **결정론 판정** | 동일 입력 → 동일 ROP/SS (LLM 판정 경로 없음) |
| **LT는 조정 레버가 아님** | 품목 계약 LT 입력 유지 · 출력 delta=0 · 리스크는 버퍼 재고로 전환 |
| **3단 파이프라인** | `input → analyze → output` (`runner.py` 단일 오케스트레이션) |
| **얇은 HTTP / 두꺼운 도메인** | `app/api`는 어댑터 · 로직은 `app/pipeline` |
| **빌드 없는 프론트** | `app/web` 정적 HTML/CSS/ES modules · FastAPI 동일 오리진 서빙 |
| **외부 API 실패 내성** | Kakao 키 없음/타임아웃 → evaluate **200** + fallback guidance |
| **표준 vs 추천 분리** | 행사·경쟁 보정은 **추천 측 D_eff** 에만 · 비교 표 표준은 미보정 D |

### 1.2 논리 구조 (런타임)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser (app/web)                                                       │
│  환영 → 위저드(기본/세부/품목) → 로딩 → 결과(비교·근거·export·시뮬)      │
│  store_picker · theme · demo_scenarios · competition_sim · report_export │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ fetch JSON (same origin)
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI (app/main.py)                                                   │
│  CORS · StaticFiles(/static) · GET / · include_router(/api)              │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   GET health/template    GET regions/places    POST evaluate/simulate
          │                     │                     │
          │                     ▼                     ▼
          │            store_search / region     pipeline.runner.run
          │            competition_sim                 │
          │                                   ┌────────┴────────┐
          │                                   ▼                 ▼
          │                              input.template    analyze.engine
          │                                   │                 │
          │                                   │    scoring · KB · geo · event
          │                                   │    · competition_saturation
          │                                   └────────┬────────┘
          │                                            ▼
          │                                   output.recommendation
          └────────────────────────────────────────────┘
```

### 1.3 요청 경로 요약

| 계층 | 경로 | 역할 |
|------|------|------|
| UI | `GET /` | 셸 HTML (버전 치환) |
| 정적 | `GET /static/*` | JS/CSS/아이콘 |
| API | `GET /api/health` | 헬스·버전·서비스 식별 |
| API | `GET /api/template` | 입력 필드 스펙 (폼 동적 생성) |
| API | `GET /api/regions/sido\|sigungu\|dong` | 행정구역 캐스케이드 |
| API | `GET /api/places/search` | 점포·주소 자동완성 (Kakao) |
| API | `POST /api/evaluate` | ROP 본 파이프라인 |
| API | `POST /api/simulate` | 경쟁·LT·수요 what-if (결정론 충격) |

---

## 2. 기술 스택과 반영 방식

### 2.1 런타임 스택

| 기술 | 버전/범위 | 프로젝트에서의 역할 |
|------|-----------|---------------------|
| **Python** | ≥3.11 | 서버·파이프라인 전역 |
| **FastAPI** | ≥0.116 | HTTP API · DI · OpenAPI |
| **Uvicorn** | ≥0.35 | ASGI 서버 (로컬·Vercel Python 런타임) |
| **Pydantic v2** | ≥2.8 | 요청/응답·내부 계약(`types.py`) 검증 |
| **pydantic-settings** | ≥2.4 | `MDPREFLIGHT_*` / `.env` 설정 |
| **orjson** | ≥3.10 | 의존성 포함 (JSON 성능; 직렬화 경로는 FastAPI 기본과 공존) |
| **urllib** (stdlib) | — | Kakao Local REST 호출 (SDK 없음) |
| **브라우저 ES modules** | 네이티브 | `type="module"` · 번들러 없음 |
| **Vercel** | `@vercel/python` | `vercel.json` → `app/main.py` 단일 엔트리 · `app/web/**` include |

### 2.2 개발·품질 스택

| 도구 | 용도 |
|------|------|
| **uv** | lock(`uv.lock`) · 실행(`uv run`) |
| **ruff** | lint (E/F/I/N/UP/B/…) |
| **basedpyright** | `typeCheckingMode=all` · `app/` only |
| **pytest** + **httpx2** | API/파이프라인/시뮬 단위·계약 테스트 |
| **Node** | `scripts/verify_*.mjs` 프론트 순수 로직 스모크 |

### 2.3 외부 연동

| 서비스 | 사용 지점 | 실패 시 |
|--------|-----------|---------|
| **Kakao Local REST** | 지오코딩 · POI · 행사 키워드 · 경쟁 검색 · 점포/동 자동완성 | fallback · evaluate 200 유지 |
| 환경 변수 | `KAKAO_REST_API_KEY` 또는 `MDPREFLIGHT_KAKAO_REST_API_KEY` | 키 없으면 검색/geo 비활성 메시지 |

### 2.4 의도적으로 넣지 않은 것 (v1 대비)

- pandas / openpyxl / multipart 업로드 검수  
- Clerk / Neon / OpenAI·Anthropic 판정 경로  
- SPA 빌드 툴체인 (Vite/Webpack 등)  
- 실시간 LLM 필수 경로  

→ **슬림 런타임**으로 배포 표면과 데모 신뢰성을 우선.

---

## 3. 디렉터리·파일별 기능

### 3.1 엔트리 · 설정 · HTTP

| 경로 | 기능 |
|------|------|
| `app/main.py` | `create_app()` · CORS · `/static` 마운트 · `/` HTML · `app` 인스턴스 |
| `app/core/config.py` | 앱명·버전(`0.3.5-rop`) · CORS 오리진 · Kakao 키 · geo 반경 |
| `app/core/errors.py` | `InputValidationError` 등 도메인 예외 |
| `app/api/routes.py` | 모든 `/api/*` 엔드포인트 (health, template, regions, places, evaluate, simulate) |
| `app/api/deps.py` | `get_app_settings` DI |
| `app/schemas/evaluate.py` | `EvaluateRequest` / `EvaluateResponse` |
| `app/schemas/places.py` | places/dong/simulate 응답 모델 re-export |

### 3.2 파이프라인 계약 · 오케스트레이션

| 경로 | 기능 |
|------|------|
| `app/pipeline/types.py` | `ValidatedInput`, `GeoEnrichment`, `CalcBreakdown`, `RecommendationResult` 등 **SSOT 계약** |
| `app/pipeline/runner.py` | `get_input_template` · `run(parameters)` = validate → analyze → render |
| `app/pipeline/domain_catalog.py` | 매장유형·규모·객단가·상권·접근성·SL·발주패턴 라벨·기본 LT 맵 |
| `app/pipeline/region_catalog.py` | 시·도 → 시·군·구 정적 캐스케이드 데이터 |

### 3.3 Input 스테이지

| 경로 | 기능 |
|------|------|
| `app/pipeline/input/template.py` | 템플릿 1.5.0 필드 정의 · 타입/범위 검증 · 유형-규모/객단가 불일치 guidance · 정확한 주소 전용 옵션 게이트 |

### 3.4 Analyze 스테이지

| 경로 | 기능 |
|------|------|
| `app/pipeline/analyze/scoring.py` | CAPA·수요집중·회전·공급난이도·변동성·접근성 리스크 일수 테이블 점수 |
| `app/pipeline/analyze/knowledge_base.py` | 행정동+품목 시드 결정론 KB · 정책 Z + 맥락 Z · 서술 노트 · FTI Z boost |
| `app/pipeline/analyze/geo_enrichment.py` | Kakao 주소→좌표 · 카테고리/버스 POI · FTI soft-sat · event/competition 스캔 오케스트레이션 |
| `app/pipeline/analyze/event_foot_traffic.py` | 200m 행사·유동 시설 프록시 · 수요 배수(최대 +35%) · FTI 블렌드 |
| `app/pipeline/analyze/competition_saturation.py` | 업태별 1차 상권 반경·직접/위협/간접 tier · 경쟁 intensity · 수요 계수(최소 0.60) |
| `app/pipeline/analyze/store_search.py` | 점포 키워드+주소 자동완성 · 읍·면·동 다중 쿼리 제안 |
| `app/pipeline/analyze/competition_sim.py` | evaluate 후 what-if: 서비스↑/경쟁 공세/LT 스트레스/수요 반등 · plain/technical 요약 |
| `app/pipeline/analyze/engine.py` | **공식 SSOT**: D_eff, LT 고정, SS, ROP, CAPA 캡, Q·요일 정책 결합 |

**핵심 공식 (엔진)**

\[
D_{\mathrm{eff}} = D \times m_{\mathrm{event}} \times f_{\mathrm{comp}}
\]
\[
SS = Z\cdot D_{\mathrm{eff}}\sqrt{LT\cdot vol/5}\cdot w_{\mathrm{turn}} + D_{\mathrm{eff}}\cdot risk\_days
\]
\[
ROP = D_{\mathrm{eff}}\cdot LT + SS \quad (\mathrm{CAPA\,시\,상한\,및\,항등\,SS})
\]

- 표준 비교 기준선은 **미보정 D** (행사·경쟁 미반영).

### 3.5 Output 스테이지

| 경로 | 기능 |
|------|------|
| `app/pipeline/output/recommendation.py` | plain/technical 이중 서술 · 비교 대시보드 · 근거 4블록(물류·수요·geo·CAPA) · 이벤트/경쟁 문구 |

### 3.6 웹 UI (`app/web`)

| 경로 | 기능 |
|------|------|
| `index.html` | 셸 · 위저드 스텝 · 테마 · 푸터 · roadmap CTA · favicon/meta |
| `styles.css` | 라이트/다크 토큰 · 위저드·결과·export·store picker·sim 패널 |
| `app.js` | 템플릿 기반 폼 · 위저드 네비 · evaluate · 결과 렌더 · expert 토글 · 시뮬 마운트 · 정확한 위치 시 행정동 숨김 |
| `wizard_logic.mjs` | 주소 필수 규칙 · payload sanitize · 에러 UI 상태 (Node 테스트 가능) |
| `store_picker.mjs` | 시·도/시·군·구 + 읍·면·동 콤보 · 점포 검색 리스트 · 선택 주소 확정 |
| `theme.mjs` | light/dark/system 테마 |
| `demo_scenarios.mjs` | 제3자 시연 프리셋 (CAPA·하이퍼·event·competition·mismatch) |
| `report_export.mjs` | PDF(print iframe)·MD·CSV·JSON 내보내기 |
| `competition_sim.mjs` | 시나리오 카드 · 충격 강도 슬라이더 설명 · 결과 캐시(전문가 토글 유지) |
| `favicon.svg` | 탭 아이콘 |

### 3.7 테스트 · 스크립트 · 배포 설정

| 경로 | 기능 |
|------|------|
| `tests/test_pipeline.py` | 엔진·CAPA·SS∝D 등 도메인 회귀 |
| `tests/test_api.py` | health/template/evaluate/static/regions/places/simulate |
| `tests/test_geo_enrichment.py` | FTI·fallback |
| `tests/test_event_foot_traffic.py` | 행사 uplift |
| `tests/test_competition_saturation.py` | 경쟁 포화 점수·D_eff |
| `tests/test_store_search.py` | 랭킹·동 검색 mock·시뮬 문구 |
| `tests/test_wizard_logic.py` | Node 스모크 래퍼 |
| `scripts/verify_*.mjs` | wizard / export / demo_scenarios 순수 로직 |
| `demo.sh` | 로컬·프로덕션 E2E 스모크 |
| `vercel.json` | Python 빌드 · `app/web/**` include · catch-all → `app/main.py` |
| `pyproject.toml` / `uv.lock` | 의존성·도구 설정 |
| `.env.example` | Kakao 키 안내 (시크릿 미커밋) |

### 3.8 문서 (계약·판)

| 경로 | 역할 |
|------|------|
| `docs/redesign/pipeline.md` | 파이프라인·공식 **SSOT** |
| `docs/redesign/board.md` | Done/Backlog (R0–R16) |
| `docs/architecture.md` | 아키텍처 요약 (버전 표기는 본 보고서로 갱신 권장) |
| `docs/setup-kakao-local.md` | Kakao 키 설정 |
| `README.md` / `PROJECT_BRIEF.md` / `AGENTS.md` | 실행·범위·에이전트 규칙 |
| `docs/dev-journal-2026-07.md` | 국면 I–X 개발 일지 |

---

## 4. 데이터 흐름 (평가 1회)

1. **UI**가 `GET /api/template`로 필드 생성 → 사용자 입력(또는 시연 프리셋).  
2. 정확한 위치 ON 시 `store_picker`가 `regions/*` · `places/search`로 공식 주소 확정 · 행정동 필드 숨김 후 지역 라벨 자동 주입.  
3. `POST /api/evaluate` → `validate_parameters` (불일치 guidance, 옵션 게이트).  
4. `analyze`: scoring → (선택) Kakao geo/event/competition → KB → 공식·CAPA.  
5. `render`: plain/technical 추천·비교·근거.  
6. UI 결과 표시 · export · (선택) `POST /api/simulate` what-if.

---

## 5. 기능 맵 (제품 기능 ↔ 코드)

| 제품 기능 | 주요 코드 |
|-----------|-----------|
| 멀티 세션 입력 위저드 | `index.html` · `app.js` · `wizard_logic.mjs` |
| 테마 light/dark/system | `theme.mjs` · `styles.css` |
| 정확한 위치 · 점포 콤보 | `store_picker.mjs` · `store_search.py` · `region_catalog.py` |
| 일시 유동 수요 증분 | `event_foot_traffic.py` · engine D_eff |
| 경쟁 포화 수요 분산 | `competition_saturation.py` · geo 스캔 |
| ROP/SS/Q/요일 추천 | `engine.py` · `knowledge_base.py` · `scoring.py` |
| 쉬운/전문 이중 해설 | `recommendation.py` · expert 토글 |
| 리포트 export | `report_export.mjs` |
| 시연 프리셋 | `demo_scenarios.mjs` |
| 경쟁 시뮬레이션 | `competition_sim.py` · `competition_sim.mjs` |
| 배포 | `vercel.json` · Vercel env Kakao 키 |

---

## 6. 배포 · 환경

```
로컬:  uv sync && uv run uvicorn app.main:app --reload --port 8000
검증:  uv run ruff check app tests && uv run basedpyright app && uv run pytest
스모크: ./demo.sh | ./demo.sh --prod
배포:  vercel deploy --prod  (Python runtime, app/web include)
```

| 환경 변수 | 용도 |
|-----------|------|
| `KAKAO_REST_API_KEY` | 지도·점포·경쟁·동 검색 |
| `MDPREFLIGHT_GEO_RADIUS_M` | POI 반경(기본 500) |
| `MDPREFLIGHT_APP_VERSION` 등 | 선택 오버라이드 |

---

## 7. 품질 현황 (기준 시점)

| 항목 | 상태 |
|------|------|
| ruff / basedpyright | app 그린 |
| pytest | **68 passed** (파이프라인·geo·event·competition·places·simulate·API) |
| 프로덕션 health | `0.3.5-rop` · `rop-adjust` |
| v1 | 태그 `archive/v1-md-preflight` · 활성 트리 미포함 |

---

## 8. 백로그 (아키텍처 확장 포인트)

| ID | 내용 | 확장 위치 |
|----|------|-----------|
| R9 | 실측 KB / 공공 데이터 | `knowledge_base.py` 포트 유지 |
| R10 | 실 Agent AI 교체 | analyze 포트 |
| R11 | 품목 마스터·단위 | input + domain_catalog |
| R12 | 발주 스케줄 캘린더 UX | web + order pattern |
| R13 | AbortController 타임아웃 UX | app.js |
| — | 실시간 행사 캘린더 | `event_foot_traffic.py` 프록시 교체 |

모듈 경계가 **스테이지·파일 단위로 이미 분리**되어 있어, 위 확장은 파이프라인 교체/추가 포트로 수용 가능하다.

---

## 9. 한 줄 결론

현재 빌드는 **FastAPI + Pydantic 결정론 3단 파이프라인**을 코어로 하고, **Kakao Local을 선택적 보강 계층**으로 얹은 뒤, **빌드 없는 멀티 세션 웹 UI**로 시연·내보내기·경쟁 시뮬레이션까지 닫은 **매장 특화 ROP 재조정 서비스**이다. 기술 스택은 의도적으로 슬림하며, 복잡도는 도메인 공식·상권 규칙·이중 서술 UX에 집중되어 있다.

---

*정본 파일: `docs/architecture-report-2026-07-16.md`*  
*관련 SSOT: `docs/redesign/pipeline.md` · `app/pipeline/analyze/engine.py` · `app/pipeline/types.py`*
