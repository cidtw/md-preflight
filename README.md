# MD Preflight

> 유통 프로모션 등록 **전에** 행사·상품·재고 파일을 검수해, 가격·기간·마진·재고·증정 조건의 운영 리스크를 사전에 잡아내는 도구.
> **핵심 원칙: 판단은 결정론적 규칙 엔진이, 서술만 LLM이 한다.**

FastAPI · Pandas · Pydantic · (선택) OpenAI / Anthropic

---

## 왜 이 프로젝트인가 — 문제

유통 프로모션은 가격, 기간, 재고, 입고일, 증정 조건, 마진, 종료 후 원복 등 여러 실행 요소가 동시에 맞아야 한다. 담당자(MD)의 작은 오입력 하나 — 행사가가 정상가보다 높거나, 시작일보다 입고일이 늦거나, 마진이 음수이거나 — 가 점포 혼선·고객 클레임·재고 부족·마진 악화로 번진다. **등록 버튼을 누르기 전에** 이 리스크를 자동 검수하는 것이 MD Preflight의 목적이다.

파일 3개(프로모션 계획 / 상품 마스터 / 재고)를 업로드하면 → 이슈 목록 · 요약 · 담당자 체크리스트 · Markdown 리포트를 돌려준다.

## 사용자 스토리 (MD의 하루)

유통 MD 김대리는 다가오는 대형 초특가 기획전 행사 등록을 앞두고 있습니다. 만약 파일 오입력으로 정상가보다 행사가가 높게 등록되거나 마진율이 음수가 되면 점포 혼선과 마진 손실을 입게 되는 상황입니다.

1. **파일 업로드**: 김대리는 프로모션 계획, 상품 마스터, 재고 파일을 MD Preflight에 업로드합니다.
2. **규칙 엔진 검수 (결정론적 판정)**: 시스템은 등록 전 10대 핵심 규칙을 순회하며 검수합니다. 이 과정에서 입고일이 행사 시작일보다 늦는 오류(`INBOUND_DATE_CONFLICT`)와 마진율이 마이너스인 오입력(`LOW_MARGIN_RATE`)을 즉시 포착합니다.
3. **AI 서술 및 체크리스트 생성**: 검수가 완료되면, 이미 판정된 이슈 목록을 바탕으로 AI가 직관적인 한국어 요약 리포트와 조치가 필요한 실행 체크리스트를 즉시 생성해 줍니다.
4. **리스크 예방**: 김대리는 요약 리포트를 통해 리스크 항목을 즉각 인지하고, 파트너사와 입고 일정을 조율하여 수억 원대의 영업 손실 및 점포 혼선을 미연에 방지합니다.

## 설계의 핵심 — 왜 판정을 LLM에 안 맡겼나

검수 판단(pass/fail)을 LLM에 맡기면 **비결정론·환각·감사 불가**라는 세 가지 문제가 생긴다. 같은 파일이 실행할 때마다 다른 결과를 낼 수 있고, "왜 이게 통과됐는가"를 설명할 수 없다. 운영·규제 도메인에서 이는 치명적이다.

그래서 이 프로젝트는 역할을 **엄격히 격리**한다.

```
                            ┌─ [무상태 판정 경로 (Stateless Path)] ────────────────────┐
                            │                                                          │
                            │   ingest ─> 판단(deterministic) ───────────┐             │
                            │             rule engine                    │             │
                            │             (10개 순수 함수 룰)             │             │
                            │             │                              │             │
                            │             ▼                              │             │
[3개 파일] ────────────────>│             list[Issue] + 판정             │             │
  업로드                    │             │                              │             │
                            │             ├───────────────────┐          │             │
                            │             ▼                   ▼          │             │
                            │           [성공]              [실패]       │             │
                            │             │                   │          │             │
                            │             ▼                   ▼          │             │
                            │           서술(LLM)           Fallback     │             │
                            │          (OpenAI/Anthropic)    (로컬)      │             │
                            │             │                   │          │             │
                            │             └─────────┬─────────┘          │             │
                            │                       ▼                    │             │
                            │                PreflightReport             │────┐        │
                            └────────────────────────────────────────────┘    │        │
                                                                              │        │
                            ┌─ [격리된 이력 & 인증 경로 (Isolated Path)] ────────┐  │ (비동기)│
                            │                                                 │  ▼        │
                            │   PreflightReport                               │ <───────┘
                            │        │                                        │
                            │        ▼ (append-only 저장)                      │
                            │   Neon Postgres (run_history)                   │
                            │        ▲                                        │
                            │        │ (선택 로그인 사용자만 조회 가능)            │
                            │   [선택적 인증 게이트]                          │
                            │   Clerk Auth / Local Stub                       │
                            │                                                 │
                            └─────────────────────────────────────────────────┘
```

- **결정론**: 같은 입력 → 항상 같은 이슈. 재현·감사 가능.
- **LLM은 판정선 밖**: LLM 생성기는 **이미 확정된 `summary`와 `issues`만** 입력받는다(타입으로 강제). 원본 셀 값·`product_name`은 프롬프트에 들어가지 않는다 → **프롬프트 주입으로 판정을 뒤집을 수 없음**(구조적 방어 + 계약 테스트로 증명).
- **교체 가능한 서술 공급자**: `OPENAI_API_KEY`(OpenAI structured outputs) 또는 `ANTHROPIC_API_KEY`(Anthropic)를 탐색하여 사용 가능한 최적의 LLM으로 서술(요약/체크리스트)을 생성합니다. LLM 키가 없거나 호출이 실패해도 결정론적 fallback 서사로 `200`을 반환합니다.
- **append-only 감사 이력**: 검수 성공 여부 및 발생 룰 집계 데이터는 Neon Postgres(`run_history` 테이블)에 추가(append-only) 저장됩니다. 이력 저장을 실패하거나 DB 가용성이 낮아도 검수 자체는 인메모리로 격리 동작하므로 API 전체 장애로 이어지지 않습니다.
- **선택적 로그인**: 검수 실행 API 자체는 비로그인 상태에서도 항시 동작(`200 OK`)하며, 이력 및 대시보드 조회 기능만 Clerk 인증 및 로컬 스텁을 경유하여 로그인 세션 기반으로 안전하게 보호됩니다.

## 검수 룰 (10개)

| Code | Severity | 무엇을 잡는가 |
|---|---|---|
| `INVALID_DATE_RANGE` | error | 시작일 > 종료일, 또는 날짜 파싱 실패 |
| `MISSING_PRODUCT_MASTER` | error | 프로모션 상품이 상품 마스터에 없음 |
| `INCOMPLETE_PRODUCT_MASTER` | error | 마스터엔 있으나 정상가/원가 결측 |
| `INVALID_PROMO_PRICE` | error | 행사가 ≤ 0 또는 행사가 > 정상가 |
| `EXTREME_DISCOUNT_RATE` | warning | 할인율 ≥ 임계값(기본 70%) |
| `LOW_MARGIN_RATE` | warning→error | 마진율 < 임계값(기본 5%), 음수면 error 승격 |
| `DUPLICATE_MASTER_CODE` | warning | 마스터/재고에 중복 상품 코드 |
| `INVENTORY_SHORTAGE_RISK` | warning | 예상 수요 > 재고 수량 |
| `INBOUND_DATE_CONFLICT` | warning | 입고일 > 행사 시작일 |
| `MISSING_BENEFIT_CONDITION` | error | 증정 유형은 있는데 조건이 공란 |

상세 판정 로직·임계값: [`docs/rule-matrix.md`](docs/rule-matrix.md) · [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md)

**룰 확장 비용이 낮다**: 룰 추가 = 파일 1개 + `app/rules/__init__.py`의 `RULES` 리스트 1줄. 플러그인 로더·데코레이터 매직 없음 → 리뷰·디버깅이 쉽다.

## 데이터 정합성 (ingest 불변식)

- `joined` 뷰는 프로모션 행과 **1:1**을 보장한다. 마스터/재고의 중복 코드는 조인 입력에서 dedup(첫 행 기준)하고, 중복 자체는 `DUPLICATE_MASTER_CODE`로 표면화한다. 조인 후 행 수가 어긋나면 `IngestError`.
- 마스터에 매칭됐지만 정상가/원가가 빈 상품은 조용히 통과시키지 않고 `INCOMPLETE_PRODUCT_MASTER`(error)로 잡는다.

## 컬럼 별칭 (헤더 유연성)

ERP·본사 양식마다 컬럼명이 달라도 검수할 수 있도록, 업로드 헤더는 **정규 키로 수렴**한 뒤 룰을 적용한다.

| 정규 키 (예시) | 허용 별칭 예 |
|---|---|
| `product_code` | `상품코드`, `품번`, `SKU` |
| `promo_price` | `행사가`, `할인가`, `프로모션가` |
| `normal_price` | `정상가`, `정가`, `판매가` |
| `stock_qty` | `재고`, `재고수량`, `현재고` |

- 별칭 표 SSOT: `app/domain/column_aliases.py`
- 적용된 매핑은 응답 필드 `column_mappings`와 Markdown 리포트 **Column Mapping** 절, UI 결과 화면에 노출 (감사 가능)
- 한글 헤더 dirty 샘플: `data/samples/alias_ko/` (웹: `/samples/alias_ko/...`)
- 설정 화면(`#/settings`)에서 읽기 전용 별칭 카탈로그 확인

## 빠른 시작

```bash
uv sync
cp .env.example .env.local   # 선택: LLM/DB/Clerk 키를 채우면 각 기능이 실 배선으로 켜진다
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

`.env.local`을 만들지 않아도(또는 비워둬도) 서버는 완전히 동작한다 — LLM은 fallback 서사, 이력은 인메모리, 인증은 `off` 모드로 degrade된다. 각 변수의 의미는 [`.env.example`](.env.example) 참고.

30초 데모 (서버 기동 → clean/dirty 검수 → 리포트):

```bash
./demo.sh
```

수동 호출 (LLM 없이 = 오프라인 안전):

```bash
curl -s -X POST http://127.0.0.1:8000/api/preflight \
  -F use_llm=false \
  -F promotion_plan=@data/samples/dirty/promotion_plan.csv \
  -F product_master=@data/samples/dirty/product_master.csv \
  -F inventory=@data/samples/dirty/inventory.csv | python -m json.tool
```

`data/samples/dirty`는 10개 룰을 각 1건씩 유발하고, `data/samples/clean`은 이슈 0건이다.  
`data/samples/alias_ko`는 dirty와 동일 이슈를 **한글/동의어 헤더**로 재현한다.

## API

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/preflight` | 전체 파이프라인. `use_llm`(기본 true) 폼 필드. |
| `POST` | `/api/preflight/validate` | 룰만 실행(LLM 생략, 항상 fallback) |
| `GET` | `/api/preflight/runs/{run_id}` | 저장된 결과 재조회 |
| `GET` | `/api/preflight/runs/{run_id}/report.md` | Markdown 리포트 다운로드 |
| `GET` | `/api/preflight/rules` | 룰 메타데이터 목록 |
| `GET` | `/api/preflight/catalog` | 설정용 읽기 전용 카탈로그 — 임계값 · 소스별 컬럼 별칭 · 룰 목록 · 업로드 한도 |
| `POST` | `/api/preflight/detect-roles` | 업로드 테이블 헤더로 정규 프레임 역할 추정(T57). `files` 멀티파트 다건 |
| `GET` | `/api/preflight/health` | 헬스체크 — `auth_mode`(`clerk`\|`stub`\|`off`) · `run_backend`/`history_backend`(`postgres`\|`in_memory`)를 비밀값 없이 노출 |

**룰 세트 버전(`rule_set_version`)**: `PreflightReport`와 이력 레코드마다 룰 코드 목록 + 임계값(`RuleThresholds`)의 결정론적 해시(sha256 앞 12자)가 찍힌다. 어떤 룰 구성이 이 리포트를 만들었는지 감사·비교하는 용도 — 같은 룰·임계값이면 항상 같은 버전, 하나라도 바뀌면 값이 달라진다.

**에러 규약**: 확장자 오류 `400` · 파일 크기 초과 `413` · 컬럼 누락/타입 오류 `422`. 개별 룰 예외는 500으로 새지 않고 격리되어 `failed_rules`에 담긴다.

**업로드 제한값 단일 출처**: `max_upload_bytes`/`allowed_extensions`는 서버 `Settings`가 유일한 정본이다. `/`가 서빙하는 index.html에 `window.__MDP_CONFIG__.maxUploadBytes`/`.allowedExtensions`로 주입되고, `app/web/config_helpers.mjs`의 `getUploadLimits()`가 이를 읽어 프런트 검증(드롭존 accept 속성, 크기/확장자 에러 메시지)에 쓴다. 주입이 없는 컨텍스트에서만 동일한 기본값(5MB, `.csv`/`.xlsx`)으로 fallback한다.

**대용량 CSV 인라인 편집 가드**: 브라우저 편집기는 셀마다 `<input>`을 렌더링하므로, 1,000행을 넘는 CSV는 `app/web/csv_tools.mjs`의 `shouldDisableInlineEditing()`이 인라인 편집을 자동 비활성화하고 안내 문구만 보여준다. 검수 자체(서버 제출)는 원본 업로드 파일을 그대로 쓰므로 영향받지 않는다.

**Run 조회 권한**: `run_id`는 검수 시점에 로그인 상태였는지에 따라 소유자가 갈린다.
- 비로그인 상태로 만든 run(소유자 없음) — `run_id`(uuid4 hex, 사실상 추측 불가) 자체가 캐퍼빌리티 토큰이라 누구나 조회 가능.
- 로그인 상태로 만든 run(소유자 있음) — `GET /api/preflight/runs/{run_id}` · `.../report.md`는 인증 없이 조회 시 `401`, 다른 사용자가 조회 시 `403`, 존재하지 않는 run_id는 `404`, 소유자 본인은 `200`.

## LLM 사용 (선택)

- 서술 공급자는 교체 가능하며, 판정은 언제나 결정론 규칙 엔진이 맡는다.
- 우선순위는 `OPENAI_API_KEY`가 있으면 OpenAI structured outputs, 없고 `ANTHROPIC_API_KEY`가 있으면 Anthropic, 둘 다 없거나 호출이 실패하면 fallback이다.
- 기본 모델은 OpenAI `gpt-5.5`, Anthropic `claude-sonnet-5`다. 둘 다 Pydantic 스키마 기반 구조화 출력을 사용한다.

```bash
export OPENAI_API_KEY=sk-proj-...
# 또는 export ANTHROPIC_API_KEY=sk-...
# 이후 use_llm=true 요청은 사용 가능한 공급자로 서사를 생성하고, 실패 시 fallback
```

## 테스트 전략

룰 유닛 테스트가 피라미드의 최대 비중이다.

```bash
uv run ruff check app tests
uv run basedpyright app tests
uv run pytest            # 132 tests, 네트워크/실 LLM 호출 없음
for f in scripts/verify_*.mjs; do node "$f"; done   # 프런트 순수 헬퍼(csv/editor/auth 등)
```

- **CI에서 실제 LLM 호출 금지** — LLM 경로는 전부 목킹. `tests/test_narrative_contract.py`가 "LLM이 판정을 못 바꾼다"를 적대적으로 증명한다(악의적 서사·프롬프트 주입·범위 이탈 케이스).
- 골든 픽스처: `data/samples/clean`(passed) / `dirty`(10룰 전부) — 회귀 안전망 겸 데모 데이터.

## 범위 밖 (의도적 제외)

실시간 POS/ERP 연동, 수요예측. 3주 MVP 스코프를 통제하기 위한 명시적 제외다. 로그인은 검수 경로가 아니라 이력 대시보드에만 선택적으로 붙는다.

## 선택 로그인 · 이력 대시보드

- 검수 파이프라인은 **비로그인도 그대로 200**이다.
- `GET /api/preflight/history?granularity=day|month|year` 와 `GET /api/preflight/history/runs` 는 로그인 상태에서만 동작한다.
- 인증 모드는 `Settings.auth_mode`(`clerk` | `stub` | `off`)로 명시적으로 결정된다: 두 Clerk 키가 모두 설정되면 `clerk`, 아니면 `MDPREFLIGHT_ALLOW_STUB_AUTH=true`(또는 `ALLOW_STUB_AUTH=true`)일 때만 `stub`, 그 외엔 `off`다.
- `clerk` 모드: `CLERK_SECRET_KEY` 와 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 가 함께 설정되면 Clerk 세션 토큰(`Authorization: Bearer ...` 또는 `__session` 쿠키)을 검증해 실제 user ID를 얻는다. 이때 `aud` 대신 `iss` 와 `azp`(허용 origin 목록) 기준으로 검증한다.
- `stub` 모드: `X-MD-Preflight-User-Id` 헤더 / `md_preflight_user_id` 쿠키를 그대로 신뢰한다 — **위조 가능**하므로 로컬 데모·테스트 전용이며 명시적으로 켜야만 활성화된다.
- `off` 모드(Clerk 미설정 + 스텁 미허용, 배포 기본값): `get_current_user_id`가 항상 `None`을 반환한다. 검수 자체는 그대로 `200`을 반환하지만(이력 저장 생략), 이력/대시보드 조회는 `401`이다.
- 이력 저장소는 `DATABASE_URL` 이 설정되면 Neon/Postgres `run_history` 테이블에 append/query 하고, 비설정 환경에서는 `InMemoryHistoryStore` 로 fallback 한다. 스토어 초기화가 실패해도 검수 요청은 메모리 스토어로 degrade 되어 200을 유지한다.
- `run_id` 전체 리포트(재조회·`.md` 다운로드용)도 같은 원칙으로 저장된다: `DATABASE_URL` 이 설정되면 `preflight_runs` 테이블(run_id·owner_user_id·report_json)에 저장하고, 비설정 시 프로세스 로컬 `InMemoryRunStore`(최대 128개, LRU)로 fallback한다. 멀티 워커/서버리스 환경에서는 `DATABASE_URL` 없이는 재조회가 인스턴스마다 갈릴 수 있다. 저장 실패는 검수 응답(`200`)을 막지 않지만, 저장이 실패한 run은 이후 재조회 시 `404`가 될 수 있다(POST 응답 본문에 이미 전체 리포트가 담겨 있으므로 최초 응답은 항상 온전하다).
- 프런트(`app/web/`)는 서버가 주입한 `window.__MDP_CONFIG__.authMode`를 그대로 읽는다. `off`일 때 로그인 버튼은 비활성화되고 "로그인 불가 — 이력은 Clerk 인증 필요"를 노출한다 — 위조 가능한 스텁 로그인을 흉내 내지 않는다.

## 문서

- [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) — 문제 정의·설계 원칙
- [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md) — 아키텍처 설계안
- [`docs/rule-matrix.md`](docs/rule-matrix.md) — 룰 판정 매트릭스
