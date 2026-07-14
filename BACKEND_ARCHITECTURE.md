# MD Preflight — 백엔드 아키텍처 설계안 (3주 MVP)

> ⚠️ **ARCHIVED (2026-07-14)** — v1 프로모션 사전검수 설계. 활성 트리는 `docs/redesign/` · `app/pipeline/`.  
> 원본 코드 복원: 태그 `archive/v1-md-preflight` · 안내 `archive/v1-md-preflight/README.md`.

> 역할: Tech Lead 설계안 · 대상: `md-preflight/` · 상태: **v1 아카이브**
> 전제: FastAPI + Pandas + Pydantic · 검수는 deterministic rule engine · LLM은 요약/체크리스트 전용(공급자 교체 가능)
> 범위 제외: ERP, POS, 로그인, 멀티테넌트, 수요예측

---

## 0. 설계 원칙 (한 줄 요약)

1. **판단은 규칙, 서술은 LLM.** rule engine이 pass/fail을 결정하고, LLM은 그 결과를 사람 말로 바꾼다. LLM은 판정에 절대 개입하지 않는다.
2. **DataFrame 하나, 규칙 여럿.** 3개 파일을 정규화한 `PreflightContext`를 만들고, 모든 룰은 이 컨텍스트를 입력받아 `list[ValidationIssue]`를 반환하는 순수 함수처럼 동작한다.
3. **추상화는 룰 등록 한 겹까지만.** Rule 프로토콜 + 리스트 레지스트리 이상은 만들지 않는다. 플러그인 로더, 이벤트 버스, DSL 없음.
4. **데모는 절대 안 죽는다.** LLM 실패/키 없음이어도 결정론적 fallback 요약·체크리스트로 200을 반환한다.

---

## 1. 폴더 구조 제안

```
md-preflight/
├─ PROJECT_BRIEF.md
├─ BACKEND_ARCHITECTURE.md        # 이 문서
├─ README.md                      # (Week 3) 문제정의·설계의도·데모 방법
├─ pyproject.toml                 # ruff + pytest + fastapi + pandas + openpyxl
├─ app/
│  ├─ main.py                     # FastAPI app factory, 라우터 등록, CORS
│  ├─ core/
│  │  ├─ config.py                # Settings(BaseSettings): 임계값, LLM 키, 모델명
│  │  └─ errors.py                # 도메인 예외 → HTTP 매핑 ( IngestError 등)
│  ├─ api/
│  │  ├─ routes.py                # 엔드포인트 (얇게 유지, 서비스 호출만)
│  │  └─ deps.py                  # Settings/서비스 의존성 주입
│  ├─ schemas/                    # 경계(API) Pydantic 모델
│  │  ├─ issue.py                 # Severity, IssueLocation, ValidationIssue
│  │  ├─ report.py                # PreflightSummary, PreflightReport
│  │  └─ rule_meta.py             # RuleMeta (GET /api/preflight/rules 응답)
│  ├─ domain/
│  │  ├─ columns.py               # 파일별 컬럼 상수 + 기대 스키마(정본)
│  │  └─ context.py               # PreflightContext (정규화된 3 DataFrame + 조인 뷰 + RuleThresholds)
│  ├─ ingest/
│  │  ├─ loader.py                # read_excel/csv → raw DataFrame
│  │  └─ normalize.py             # 컬럼 검증·타입 캐스팅·조인 → PreflightContext
│  ├─ rules/
│  │  ├─ __init__.py              # RULES 레지스트리(리스트)
│  │  ├─ base.py                  # Rule 프로토콜, Severity, issue 헬퍼
│  │  ├─ date_range.py            # INVALID_DATE_RANGE
│  │  ├─ product_master.py        # MISSING_PRODUCT_MASTER
│  │  ├─ incomplete_master.py     # INCOMPLETE_PRODUCT_MASTER
│  │  ├─ promo_price.py           # INVALID_PROMO_PRICE
│  │  ├─ discount_rate.py         # EXTREME_DISCOUNT_RATE
│  │  ├─ margin_rate.py           # LOW_MARGIN_RATE
│  │  ├─ duplicate_master_code.py # DUPLICATE_MASTER_CODE
│  │  ├─ inventory.py             # INVENTORY_SHORTAGE_RISK
│  │  ├─ inbound_date.py          # INBOUND_DATE_CONFLICT
│  │  └─ benefit_condition.py     # MISSING_BENEFIT_CONDITION
│  └─ services/
│     ├─ validation_engine.py     # ingest → 룰 실행 → PreflightReport 조립 (오케스트레이터)
│     ├─ llm_service.py           # 결정된 summary/issues를 공급자(OpenAI/Anthropic) 서사로 변환
│     └─ report_service.py        # PreflightReport → Markdown 렌더 (PDF는 계획, P2)
├─ data/
│  └─ samples/
│     ├─ clean/                   # 이슈 0건 세트 (csv/xlsx 3종)
│     └─ dirty/                   # 10개 룰을 유발하는 세트 (csv/xlsx 3종)
└─ tests/
   ├─ conftest.py                 # DataFrame/Context 빌더 팩토리
   ├─ test_rules.py               # 룰 판정/심각도/임계값 테스트
   ├─ test_loader.py              # ingest/loader 검증
   ├─ test_services.py            # 엔진 통합 + fallback + 리포트 렌더
   └─ test_api.py                 # TestClient 업로드 → 응답 shape 검증
```

**의도**
- `rules/`가 프로젝트의 심장임을 폴더 구조만 봐도 알 수 있게 최상단 노출 (포트폴리오 가독성).
- `schemas`(경계) ↔ `domain`(내부) 분리: 프론트가 쓰는 모델과 내부 계산 모델이 섞이지 않는다. 단, 과분리 방지를 위해 서비스/리포지토리 계층은 만들지 않는다(파일 3개짜리 인메모리 파이프라인이라 불필요).

---

## 2. 핵심 도메인 모델

### 2.1 입력 스키마 (정본: `domain/columns.py`)

각 파일의 기대 컬럼을 상수로 고정한다. 정규화 단계에서 이 정의로 검증한다.

| 파일 | 핵심 컬럼 |
|------|-----------|
| `promotion_plan` | `promotion_id, product_code, start_date, end_date, promo_price, benefit_type, benefit_condition` |
| `product_master` | `product_code, product_name, normal_price, cost` |
| `inventory` | `product_code, stock_qty, inbound_date, expected_demand` |

> `expected_demand`는 파일에 있는 값을 그대로 사용한다(수요예측 아님, 담당자 입력값).

### 2.2 PreflightContext (`domain/context.py`)

룰이 입력받는 유일한 객체. Pandas 조인까지 미리 해 둔다.

```python
@dataclass(frozen=True)
class PreflightContext:
    promotions: pd.DataFrame      # 정규화된 promotion_plan
    products: pd.DataFrame        # 정규화된 product_master (index=product_code)
    inventory: pd.DataFrame       # 정규화된 inventory (index=product_code)
    joined: pd.DataFrame          # promotions LEFT JOIN products/inventory (룰 대부분이 이걸 사용)
    thresholds: Thresholds        # 룰 임계값 (config에서 주입, 결정론성 보장)
```

`joined`를 미리 만들어 두면 각 룰이 조인 로직을 반복하지 않고, `MISSING_PRODUCT_MASTER`는 조인 결과의 NaN으로 바로 판정된다.

### 2.3 ValidationIssue (`schemas/issue.py`) — 프론트 친화 계약

```python
class Severity(str, Enum):
    ERROR = "error"       # 등록 차단급 (잘못된 가격/기간/미등록 상품)
    WARNING = "warning"   # 검토 필요 (극단 할인, 저마진, 재고 위험)
    INFO = "info"         # 참고

class IssueLocation(BaseModel):
    file: str                 # "promotion_plan"
    row: int | None           # 원본 행 번호(1-based, 엑셀 점프용)
    column: str | None        # "promo_price"

class ValidationIssue(BaseModel):
    code: str                 # "INVALID_PROMO_PRICE" (안정 키: i18n/그룹핑/필터)
    severity: Severity
    title: str                # "행사가가 정상가보다 높음" (한국어 요약)
    message: str              # 사람이 읽는 상세 설명
    entity: dict[str, str]    # {"promotion_id": "...", "product_code": "..."} 그룹핑 키
    location: IssueLocation   # 어느 셀인지 → 프론트 "해당 행 보기"
    observed: str | None      # 관측값 "12,000원"
    expected: str | None      # 기준 "정상가 10,000원 이하"
    suggestion: str | None    # 조치 힌트
    rule_version: str = "1"
```

**프론트가 좋아하는 이유**: `code`로 그룹/필터, `severity`로 색상, `entity`로 프로모션 단위 롤업, `location`으로 원본 셀 점프, `observed/expected/suggestion`으로 별도 계산 없이 카드 렌더.

### 2.4 PreflightReport (`schemas/report.py`) — 최종 응답

```python
class PreflightSummary(BaseModel):
    total_issues: int
    by_severity: dict[str, int]      # {"error": 3, "warning": 5, "info": 0}
    by_rule: dict[str, int]          # {"INVALID_PROMO_PRICE": 2, ...}
    passed: bool                     # error 0건이면 True
    checked_rows: int

class PreflightReport(BaseModel):
    run_id: str
    summary: PreflightSummary
    issues: list[ValidationIssue]
    ai_summary: str | None           # LLM 요약 (fallback 시 템플릿 문자열)
    checklist: list[str]             # 담당자 실행 체크리스트
    generated_by: Literal["llm", "fallback"]   # 현재는 T6 전까지 "fallback"으로 고정
    failed_rules: list[str]          # 예외로 스킵된 룰 code 목록
```

- `generated_by`는 스키마상 `llm | fallback`이고, 실제 공급자 성공 시 `llm`, 키 없음/장애 시 `fallback`이다.
- `failed_rules`는 개별 룰 예외를 전체 500으로 터뜨리지 않고 격리했을 때, 스킵된 룰 code를 담는 실제 응답 필드다.

---

## 3. 검수 엔진 흐름 (`services/validation_engine.py`)

```
[3개 파일 업로드]
      │  UploadFile × 3 (promotion_plan / product_master / inventory)
      ▼
① ingest.loader           read_excel/csv → raw DataFrame 3개
      ▼
② ingest.normalize        컬럼 존재/타입 검증, 날짜·숫자 캐스팅, 조인
      │                    실패 시 IngestError → 422 (룰 실행 안 함)
      ▼
   PreflightContext        promotions / products / inventory / joined / thresholds
      ▼
③ rule engine             for rule in RULES: issues += rule.apply(ctx)
      │                    각 룰은 순수·결정론적. 예외는 격리(한 룰 실패가 전체를 막지 않음)
      ▼
   list[ValidationIssue]
      ▼
④ summary 집계            심각도/룰별 카운트, passed 판정 → PreflightSummary
      ▼
⑤ llm_service             결정된 `summary`/`issues`만 받아 공급자(OpenAI/Anthropic) 서사 생성
      │                    키 없음·SDK 오류·파싱 실패 시 fallback으로 자동 전환
      ▼
   PreflightReport         (⑥ report_service가 요청 시 Markdown으로 렌더, PDF는 계획)
```

### 3.1 Rule 계약 (`rules/base.py`)

```python
class Rule(Protocol):
    code: str
    severity: Severity
    description: str
    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]: ...
```

- 모듈별로 룰 1개(클래스 인스턴스) 정의, `rules/__init__.py`의 `RULES: list[Rule]` 리스트에 추가.
- **룰 추가 = 파일 1개 + 리스트 1줄.** 로더/데코레이터 매직 없음 → 리뷰·디버깅 쉬움.
- 룰은 Pandas 벡터 연산으로 조건 마스크를 만들고, 해당 행을 순회하며 `ValidationIssue`를 생성.

### 3.2 10개 룰 판정 정의

| code | severity | 판정 로직(요지) | 임계값 |
|------|----------|-----------------|--------|
| `INVALID_DATE_RANGE` | error | `start_date > end_date` 또는 날짜 파싱 실패 | — |
| `MISSING_PRODUCT_MASTER` | error | `product_code`가 product_master에 없음(조인 `left_only`) | — |
| `INCOMPLETE_PRODUCT_MASTER` | error | 마스터 매칭 성공(`left_only` 아님)이나 `normal_price` 또는 `cost` 결측(NaN) | — |
| `INVALID_PROMO_PRICE` | error | `promo_price <= 0` 또는 `promo_price > normal_price` | — |
| `EXTREME_DISCOUNT_RATE` | warning | `normal_price > 0`, `promo_price > 0`, `promo_price <= normal_price`일 때 할인율 `1 - promo/normal` ≥ 임계 | `max_discount_rate=0.7` |
| `LOW_MARGIN_RATE` | warning¹ | `promo_price > 0`일 때 마진율 `(promo - cost)/promo` < 임계 | `min_margin_rate=0.05` |
| `DUPLICATE_MASTER_CODE` | warning | product_master 또는 inventory에 동일 `product_code`가 중복 존재(원본 프레임 기준) | — |
| `INVENTORY_SHORTAGE_RISK` | warning | `expected_demand > stock_qty` | — |
| `INBOUND_DATE_CONFLICT` | warning | `inbound_date > start_date` (행사 시작 후 입고) | — |
| `MISSING_BENEFIT_CONDITION` | error | `benefit_type` 값이 있는데 `benefit_condition`이 비어 있음 | — |

¹ 기본 severity 메타데이터는 `warning`이지만, 실제 issue 생성 시 계산된 마진율이 음수면 `error`로 승격된다.

> **조인 불변식(ingest):** `normalize.build_context`는 join 입력(products/inventory)을 `product_code` 기준 `drop_duplicates(keep="first")`로 정규화해 `joined`가 `promotions`와 1:1(행 수 동일)임을 보장하고, 사후에 `len(joined) != len(promotions)`이면 `IngestError`를 던진다. 중복 자체는 삭제로 숨기지 않고 `DUPLICATE_MASTER_CODE`로 표면화한다. `INCOMPLETE_PRODUCT_MASTER`는 `MISSING_PRODUCT_MASTER`(마스터 자체 없음)와 겹치지 않도록 `left_only`를 제외하며, 기존 가격/마진/할인 룰이 스킵하던 결측(NaN) 행을 명시적으로 소유한다.

### 3.3 LLM 경계 (`services/llm_service.py`)

- **현재 구현**: `FallbackNarrativeGenerator`, Anthropic용 `LLMNarrativeGenerator`, OpenAI용 `OpenAINarrativeGenerator`, `FallbackOnErrorNarrativeGenerator`가 존재한다. 입력은 확정된 `PreflightSummary` + `list[ValidationIssue]`, 출력은 `ai_summary`, `checklist`, `source`(`llm`/`fallback`)다.
- **동작 방식**: `use_llm=false`면 무조건 fallback을 사용한다. `use_llm=true`면 `OPENAI_API_KEY` 우선, 없으면 `ANTHROPIC_API_KEY`, 둘 다 없거나 SDK 예외/parse 실패가 나면 자동으로 fallback으로 전환한다.
- **프롬프트 경계**: LLM에는 `summary`와 issue의 제한된 필드(`code`, `severity`, `title`, `observed`, `expected`, `suggestion`)만 전달된다. 판정 데이터(`issues`, `summary`, `passed`)는 규칙 엔진 결과가 그대로 유지되고, LLM은 서술만 담당한다.
- **`generated_by`**: 실제로 LLM 서사가 성공하면 `"llm"`, fallback 경로면 `"fallback"`이다. `/api/preflight/validate`는 룰 전용 경로라 항상 fallback을 반환한다.
- **의미**: 현재 `llm_service.py`는 "규칙 엔진 결과를 서술로 변환하는 경계"다. 데모는 fallback으로 항상 살아 있고, LLM은 성공 시에만 narrative 계층에 개입한다.

---

## 4. API 설계

동기 처리(파일 작고 룰이 밀리초). 상태 저장은 인메모리 `dict[run_id, PreflightReport]` (TTL/최근 N개)로 시작 — DB 불필요.

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/preflight/validate` | 3파일 multipart 업로드 → ingest + rule engine → `PreflightReport` (항상 fallback 서사) |
| `POST` | `/api/preflight` | 3파일 multipart 업로드 → 전체 파이프라인. `use_llm=true`면 사용 가능한 공급자(OpenAI/Anthropic) narrative를 시도하고 실패 시 fallback |
| `GET` | `/api/preflight/runs/{run_id}` | 저장된 결과 재조회 |
| `GET` | `/api/preflight/runs/{run_id}/report.md` | Markdown 리포트 다운로드 |
| `GET` | `/api/preflight/runs/{run_id}/report.pdf` | 계획만 존재 (P2), 현재 라우트 없음 |
| `GET` | `/api/preflight/rules` | 룰 메타데이터 목록(code/severity/description) |
| `GET` | `/api/preflight/health` | 헬스체크 |
| `GET` | `/api/preflight/history?granularity=day|month|year` | 로그인 사용자 검수 이력 집계 조회 |

**요청 예 (`POST /api/preflight`)**: `multipart/form-data`
- `promotion_plan`: file, `product_master`: file, `inventory`: file
- `use_llm`: bool = true (활성화 시 사용 가능한 공급자 API 연동 서술 생성, 비활성화 혹은 호출 실패 시 fallback 자동 전환)

**응답**: `PreflightReport` (§2.4).

**에러 규약** (`core/errors.py`):
- `422` — 컬럼 누락/타입 오류·빈 업로드 등 `IngestError`. 현재 코드가 실제로 처리하는 유효성 실패 경로다.
- `400` — 파일 개수/허용 확장자(`.csv`, `.xlsx`) 외 업로드 시 `UploadValidationError` 발생.
- `413` — 단일 파일 크기(5MB) 제한 초과 시 `UploadValidationError` 발생.
- 룰 실행 중 개별 룰 예외는 500으로 새지 않고 격리(로그 + 스킵), 응답은 200.

라우터는 얇게: 업로드를 `build_uploaded_context(...)`로 넘기고 `validate_context(...)` 호출만 수행한다. 비즈니스 로직은 서비스에 둔다.

## 4.2 인증 seam (선택 로그인)

- 검수 라우트(`POST /api/preflight`, `/validate`)는 **인증 없이도 동작**한다.
- `CLERK_SECRET_KEY` 와 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 가 함께 있으면 서버는 `Authorization: Bearer <token>` 또는 `__session` 쿠키의 Clerk 세션 토큰을 검증해 실제 user ID를 얻는다.
- 두 키가 없으면 요청 헤더 `X-MD-Preflight-User-Id` 또는 쿠키 `md_preflight_user_id`를 읽는 스텁 경로로 fallback 하므로 테스트와 데모는 가볍게 유지된다.
- user ID가 확보된 경우에만 판정 완료 뒤 `RunHistoryRecord`를 append-only 이력 스토어에 저장한다.

## 부록 A. 이력 영속화 스키마

이력 저장은 규칙 엔진 밖의 append-only 감사 로그이며, **원본 파일·셀값·PII를 저장하지 않고 판정 집계만** 남긴다.

```sql
run_history(
  id            bigserial primary key,
  user_id       text not null,
  run_id        text not null,
  created_at    timestamptz not null default now(),
  passed        boolean not null,
  error_count   integer not null,
  warning_count integer not null,
  total_issues  integer not null,
  rules_triggered jsonb not null,
  source_label  text
)
```

- 현재 구현은 `HistoryStore` 프로토콜 뒤에 `PostgresHistoryStore` 와 `InMemoryHistoryStore` 를 함께 두고, `DATABASE_URL` 이 있으면 Postgres/Neon으로 실배선한다.
- 집계는 `date_trunc('day'|'month'|'year', created_at)`에 해당하는 버킷으로 합산한다.
- `DATABASE_URL_UNPOOLED` 가 있으면 DDL과 인덱스 생성을 여기에 우선 연결하고, 없으면 런타임 URL로 스키마를 보장한다.

## 4.1 입력 소스 추상화 (로드맵)

- 현재 활성 입력 경로는 멀티파트 업로드뿐이지만, 장기적으로는 모든 입력 소스를 동일한 tabular shape로 정규화한다.
- 개념적 프로토콜은 `TabularSource.fetch() -> LoadedTable`이며, 업로드 경로는 이 프로토콜의 첫 구현으로 본다.
- 예정 소스:
  - `upload` — available
  - `notion` — planned
  - `google_sheets` — planned
  - `csv_url` — planned
- 어떤 소스를 거쳐 오더라도 ingest 이후에는 동일한 정규화/룰 엔진을 사용하므로 판정은 소스와 무관하게 유지된다.
- 외부 토큰은 향후에도 요청당 전달을 기본으로 고려하고, 서버에 장기 저장하지 않는 방향이 무상태 원칙과 가장 잘 맞는다.

---

## 5. 테스트 전략

**테스트 피라미드: 룰 유닛테스트가 최대 비중.** (리뷰 기준 "핵심 룰 커버리지"에 직결)

| 계층 | 대상 | 방식 | 비중 |
|------|------|------|------|
| Unit — rules | 10개 룰 각각 | 인메모리 `PreflightContext` 빌더로 pass 1 + 각 실패모드 케이스 (룰당 3~5) | ★★★★★ |
| Unit — ingest | 컬럼 누락/타입불량/날짜파싱 | 작은 DataFrame·임시 xlsx | ★★★ |
| Integration — engine | ingest→룰→summary 전 구간 | `data/samples/dirty` → 기대 이슈 집합 스냅샷 | ★★★ |
| Service — llm | 프롬프트 조립 + fallback | LLM 클라이언트 **목킹**, 실제 API 호출 금지 | ★★ |
| Service — report | Markdown 렌더 | 스냅샷 비교 | ★ |
| API | 업로드 흐름·에러코드 | `TestClient` + `data/samples/{clean,dirty}` | ★★ |

**규칙**
- CI에서 **실제 LLM 호출 금지** (목킹/fallback). 룰·엔진 테스트는 네트워크·파일 IO 없이 순수 DataFrame으로.
- `conftest.py`에 `make_context(promotions=..., products=..., inventory=...)` 팩토리를 두어 각 룰 테스트가 최소 데이터로 독립 실행되게 한다 (리뷰 기준 "독립 테스트 가능성").
- 골든 샘플 2종: `data/samples/clean`(passed=True, 이슈 0) / `data/samples/dirty`(8룰 전부 유발) — 회귀 안전망 + 데모 데이터 겸용.
- 목표 커버리지: `rules/` ≥ 90%, 전체 ≥ 80%.

---

## 6. 구현 우선순위 (3주)

### Week 1 — 결정론 코어 (데모 없이도 "검수됨"이 증명되는 상태)
- P0: `domain/columns.py`, `domain/context.py`, `ingest/loader+normalize`
- P0: `schemas/issue.py` (`ValidationIssue`/`Severity`) 확정 — **프론트 계약 조기 동결**
- P0: 룰 4개 — `date_range`, `product_master`, `promo_price`, `margin_rate` + 각 유닛테스트
- P0: `validation_engine.run()` + `POST /api/preflight/validate` (LLM 없이)
- 완료 기준: dirty 픽스처 넣으면 이슈 JSON이 나온다.

### Week 2 — 룰 완성 + 프론트 연동 가능 상태
- P0: 나머지 룰 4개 — `discount_rate`, `inventory`, `inbound_date`, `benefit_condition` + 테스트
- P0: summary 집계, `POST /api/preflight`(현재는 fallback-only), `GET /api/preflight/rules`, `GET /api/preflight/runs/{run_id}`
- P1: `report_service` Markdown 렌더 + `report.md` 다운로드
- P1: API 테스트, 인메모리 run 저장, CORS/에러 규약 정리
- 완료 기준: 프론트가 실제 응답으로 이슈 리스트·요약 화면을 그린다.

### Week 3 — LLM 서술 + 포트폴리오 마감
- P0: 실제 LLM 연동(T6) + `generated_by="llm"` 경로 추가
- P1: PDF 리포트 라우트/렌더 추가
- P1: **README** (문제정의·설계의도·룰/LLM 역할분리·데모 방법) ← 포트폴리오 핵심
- P2: 데모 스크립트/시드 데이터 정리, 엣지 픽스처 보강
- 완료 기준: 오프라인에서도 업로드→요약→체크리스트→리포트가 끊김 없이 시연된다.

**우선순위 원칙**: "결정론 파이프라인 → 프론트 연동 → LLM 서술" 순서. LLM은 마지막에 얹어도 시스템 가치가 성립하도록 배치(리스크 후행).

---

## 부록. 후속 리뷰(2·3번 과제) 연결

- 본 설계의 `rules/`(모듈=룰, `RULES` 리스트) + `services/validation_engine.py` 구조는 **2번 과제(아키텍처 리뷰)** 기준 5개(독립 테스트성·결정론·ValidationIssue 프론트 적합성·룰 확장성·복잡도)에 그대로 대응하도록 잡았다.
- README·역할분리·테스트 커버리지·데모 안정성(fallback)은 **3번 과제(포트폴리오 리뷰)** 기준에 대응. 구현 완료 후 2·3번 리뷰를 실코드 대상으로 수행한다.
