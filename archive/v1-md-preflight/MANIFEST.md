# v1 MANIFEST — 아카이브 인벤토리

태그 `archive/v1-md-preflight` 기준. 활성 트리에서는 제거·대체되었을 수 있다.

## 패키지·모듈

| 경로 | 역할 | 재설계 후 처리 |
|------|------|----------------|
| `app/main.py` | FastAPI 앱·SPA 마운트 | 슬림 교체 |
| `app/api/routes.py` | preflight·history·catalog·detect-roles 등 | 파이프라인 API로 교체 |
| `app/api/deps.py` | store/LLM/auth DI | 슬림 교체 |
| `app/core/config.py` | 설정 (Clerk/DB/LLM/업로드) | 슬림 교체 |
| `app/core/rule_config.py` | 룰 임계값 | v1 전용 → 아카이브 |
| `app/core/errors.py` | Ingest/Upload 에러 | 일부 개념만 이관 |
| `app/domain/*` | columns, aliases, role_detect, context | v1 전용 → 아카이브 |
| `app/ingest/*` | loader, normalize | v1 전용 → 아카이브 |
| `app/rules/*` | 10룰 순수 함수 | v1 전용 → 아카이브 |
| `app/schemas/*` | report, issue, history, catalog… | v1 전용 → 아카이브 |
| `app/services/*` | validation_engine, LLM, history, clerk… | v1 전용 → 아카이브 |
| `app/sources/*` | 외부 소스 스텁 | **폐기 후보** |
| `app/web/*` | SPA 모듈 다수 + samples | 최소 셸로 교체; 샘플은 태그 보관 |

## API 표면 (v1)

- `POST /api/preflight`, `POST /api/preflight/validate`
- `GET /api/preflight/runs/{id}`, `.../report.md`
- `GET /api/preflight/rules`, `/catalog`, `/sources`
- `POST /api/preflight/detect-roles`
- `GET /api/preflight/history`, `/history/runs`
- `GET /api/preflight/health`

## 프론트 모듈 (v1 `app/web`)

`app.js`, `router.mjs`, `csv_tools.mjs`, `editor_state.mjs`, `history_dashboard.mjs`,  
`issue_view.mjs`, `report_view.mjs`, `auth_*.mjs`, `config_helpers.mjs`, `theme.mjs` 등  
→ 웹표준 준수는 유지하되 제품 스코프 대비 과다 → **활성 경로에서 제거**.

## 문서·발표 산출

| 경로 | 비고 |
|------|------|
| `BACKEND_ARCHITECTURE.md`, `DESIGN.md`, `PROJECT_BRIEF.md` | v1 서술 (브리프는 재작성) |
| `docs/architecture-easy.md`, `architecture-input-flexibility-decision.md` | v1 |
| `docs/adr/0001-input-adapter-canonical-frames.md` | v1 ADR |
| `docs/rule-matrix.md` | v1 10룰 |
| `docs/dev-journal-2026-07.md` | **유지·연장** (국면 VI 기록) |
| `slides/`, `slide-outline.md` | 중간발표 자산 (로컬/repo 상태 유지, 제품 경로 비의존) |
| `handoff/` | gitignore 로컬 히스토리 |

## 테스트 (v1)

`tests/test_rules.py`, `test_api.py`, `test_column_aliases.py`, `test_role_detect.py`,  
`test_history_store.py`, `test_clerk_auth.py`, … 전체 프로모션 검수 스위트  
→ 태그에서 재현 가능. 활성 트리는 파이프라인 스켈레톤 테스트로 교체.

## 의존성 (v1 특징)

pandas, openpyxl, anthropic, openai, psycopg, PyJWT — 파일 검수·LLM·Neon·Clerk용.  
재설계 스켈레톤은 기본적으로 **표준 라이브러리 + FastAPI + Pydantic** 중심.
