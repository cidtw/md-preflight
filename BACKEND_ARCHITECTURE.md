# MD Preflight — 백엔드 아키텍처 설계안 (3주 MVP)

> 역할: Tech Lead 설계안 · 대상: `md-preflight/` · 상태: 설계 확정용 초안
> 전제: FastAPI + Pandas + Pydantic · 검수는 deterministic rule engine · LLM은 요약/체크리스트 전용
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
├─ pyproject.toml                 # ruff + pytest + fastapi + pandas + openpyxl + anthropic
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
│  │  └─ rule_meta.py             # RuleMeta (GET /rules 응답)
│  ├─ domain/
│  │  ├─ columns.py               # 파일별 컬럼 상수 + 기대 스키마(정본)
│  │  └─ context.py               # PreflightContext (정규화된 3 DataFrame + 조인 뷰)
│  ├─ ingest/
│  │  ├─ loader.py                # read_excel/csv → raw DataFrame
│  │  └─ normalize.py             # 컬럼 검증·타입 캐스팅·조인 → PreflightContext
│  ├─ rules/
│  │  ├─ __init__.py              # RULES 레지스트리(리스트) + ALL_RULE_META
│  │  ├─ base.py                  # Rule 프로토콜, Severity, issue 헬퍼
│  │  ├─ date_range.py            # INVALID_DATE_RANGE
│  │  ├─ product_master.py        # MISSING_PRODUCT_MASTER
│  │  ├─ promo_price.py           # INVALID_PROMO_PRICE
│  │  ├─ discount_rate.py         # EXTREME_DISCOUNT_RATE
│  │  ├─ margin_rate.py           # LOW_MARGIN_RATE
│  │  ├─ inventory.py             # INVENTORY_SHORTAGE_RISK
│  │  ├─ inbound_date.py          # INBOUND_DATE_CONFLICT
│  │  └─ benefit_condition.py     # MISSING_BENEFIT_CONDITION
│  └─ services/
│     ├─ validation_engine.py     # ingest → 룰 실행 → PreflightReport 조립 (오케스트레이터)
│     ├─ llm_service.py           # 요약+체크리스트 생성 (결정론적 fallback 포함)
│     └─ report_service.py        # PreflightReport → Markdown/PDF 렌더
└─ tests/
   ├─ conftest.py                 # DataFrame/Context 빌더 팩토리
   ├─ fixtures/
   │  ├─ clean/                   # 이슈 0건 세트 (xlsx 3개)
   │  └─ dirty/                   # 8개 룰 전부 유발하는 세트
   ├─ rules/                      # 룰당 1개 테스트 파일 (핵심 커버리지)
   ├─ ingest/                     # 스키마/타입/누락 컬럼 테스트
   ├─ services/                   # 엔진 통합 + llm fallback + 리포트 렌더
   └─ api/                        # TestClient 업로드 → 응답 shape 검증
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
    generated_by: Literal["llm", "fallback"]   # 데모 투명성
```

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
⑤ llm_service (선택)      결정론적 결과 → LLM 요약 + 체크리스트
      │                    키 없음/타임아웃/에러 → 결정론적 fallback (generated_by="fallback")
      ▼
   PreflightReport         (⑥ report_service가 요청 시 Markdown/PDF로 렌더)
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

### 3.2 8개 MVP 룰 판정 정의

| code | severity | 판정 로직(요지) | 임계값 |
|------|----------|-----------------|--------|
| `INVALID_DATE_RANGE` | error | `start_date > end_date` 또는 날짜 파싱 실패 | — |
| `MISSING_PRODUCT_MASTER` | error | `product_code`가 product_master에 없음(조인 NaN) | — |
| `INVALID_PROMO_PRICE` | error | `promo_price <= 0` 또는 `promo_price > normal_price` | — |
| `EXTREME_DISCOUNT_RATE` | warning | 할인율 `1 - promo/normal` ≥ 임계 | `max_discount_rate=0.7` |
| `LOW_MARGIN_RATE` | warning¹ | 마진율 `(promo - cost)/promo` < 임계 | `min_margin_rate=0.05` |
| `INVENTORY_SHORTAGE_RISK` | warning | `expected_demand > stock_qty` | (선택) `buffer_ratio` |
| `INBOUND_DATE_CONFLICT` | warning | `inbound_date > start_date` (행사 시작 후 입고) | — |
| `MISSING_BENEFIT_CONDITION` | error² | `benefit_type` 있는데 `benefit_condition` 공란 | — |

¹ 마진이 음수면 `error`로 승격. ² 조건 자체가 무의미하면 `warning`. 승격 기준도 config 상수로 고정해 결정론 유지.

### 3.3 LLM 경계 (`services/llm_service.py`)

- **입력**: `PreflightSummary` + `list[ValidationIssue]` (이미 확정된 사실).
- **출력**: (a) 3~5문장 한국어 요약, (b) 우선순위 정렬된 체크리스트 `list[str]`.
- **프롬프트 규약**: "아래 검수 결과를 재판단하지 말고, 있는 그대로 담당자용으로 요약/체크리스트화하라. 새 이슈를 만들지 마라." → LLM이 판정을 못 만들게 명시.
- **fallback**: 키 없음/에러/타임아웃 시 템플릿 기반 생성 — 심각도순으로 이슈를 문장화하고 체크리스트는 `code`별 정형 문구. `generated_by="fallback"`로 표시. **데모 안정성의 핵심.**
- Claude 최신 모델 사용(`claude-sonnet-5` 권장, 비용/속도 균형). 온도 낮게, JSON 강제 스키마로 파싱 안전.

---

## 4. API 설계

동기 처리(파일 작고 룰이 밀리초). 상태 저장은 인메모리 `dict[run_id, PreflightReport]` (TTL/최근 N개)로 시작 — DB 불필요.

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/preflight` | 3파일 multipart 업로드 → 전체 파이프라인 → `PreflightReport` (LLM 포함) |
| `POST` | `/api/preflight/validate` | 룰만 실행(LLM 생략). 빠른 결정론 경로 / 테스트·디버그용 |
| `GET` | `/api/preflight/{run_id}` | 저장된 결과 재조회 |
| `GET` | `/api/preflight/{run_id}/report.md` | Markdown 리포트 다운로드 |
| `GET` | `/api/preflight/{run_id}/report.pdf` | PDF 리포트 다운로드 (Week 3) |
| `GET` | `/api/rules` | 룰 메타데이터 목록(code/severity/description) — 프론트 룰 안내 |
| `GET` | `/health` | 헬스체크 |

**요청 예 (`POST /api/preflight`)**: `multipart/form-data`
- `promotion_plan`: file, `product_master`: file, `inventory`: file
- `use_llm`: bool = true (false면 fallback 강제 — 데모 시 오프라인 대비)

**응답**: `PreflightReport` (§2.4).

**에러 규약** (`core/errors.py`):
- `422` — 컬럼 누락/타입 오류(IngestError). `detail`에 어떤 파일·어떤 컬럼인지 구조화.
- `413` — 파일 크기 초과. `400` — 파일 개수/확장자 오류.
- 룰 실행 중 개별 룰 예외는 500으로 새지 않고 격리(로그 + 스킵), 응답은 200.

라우터는 얇게: 파싱/검증 후 `validation_engine.run(...)` 호출만. 비즈니스 로직은 서비스에.

---

## 5. 테스트 전략

**테스트 피라미드: 룰 유닛테스트가 최대 비중.** (리뷰 기준 "핵심 룰 커버리지"에 직결)

| 계층 | 대상 | 방식 | 비중 |
|------|------|------|------|
| Unit — rules | 8개 룰 각각 | 인메모리 `PreflightContext` 빌더로 pass 1 + 각 실패모드 케이스 (룰당 3~5) | ★★★★★ |
| Unit — ingest | 컬럼 누락/타입불량/날짜파싱 | 작은 DataFrame·임시 xlsx | ★★★ |
| Integration — engine | ingest→룰→summary 전 구간 | `fixtures/dirty` → 기대 이슈 집합 스냅샷 | ★★★ |
| Service — llm | 프롬프트 조립 + fallback | LLM 클라이언트 **목킹**, 실제 API 호출 금지 | ★★ |
| Service — report | Markdown 렌더 | 스냅샷 비교 | ★ |
| API | 업로드 흐름·에러코드 | `TestClient` + fixtures | ★★ |

**규칙**
- CI에서 **실제 LLM 호출 금지** (목킹/fallback). 룰·엔진 테스트는 네트워크·파일 IO 없이 순수 DataFrame으로.
- `conftest.py`에 `make_context(promotions=..., products=..., inventory=...)` 팩토리를 두어 각 룰 테스트가 최소 데이터로 독립 실행되게 한다 (리뷰 기준 "독립 테스트 가능성").
- 골든 픽스처 2종: `clean`(passed=True, 이슈 0) / `dirty`(8룰 전부 유발) — 회귀 안전망 + 데모 데이터 겸용.
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
- P0: summary 집계, `POST /api/preflight`(LLM 미포함으로 우선), `GET /api/rules`, `GET /{run_id}`
- P1: `report_service` Markdown 렌더 + `report.md` 다운로드
- P1: API 테스트, 인메모리 run 저장, CORS/에러 규약 정리
- 완료 기준: 프론트가 실제 응답으로 이슈 리스트·요약 화면을 그린다.

### Week 3 — LLM 서술 + 포트폴리오 마감
- P0: `llm_service` 요약+체크리스트 + **결정론적 fallback** + `use_llm` 플래그
- P1: PDF 리포트, `generated_by` 노출
- P1: **README** (문제정의·설계의도·룰/LLM 역할분리·데모 방법) ← 포트폴리오 핵심
- P2: 데모 스크립트/시드 데이터 정리, 엣지 픽스처 보강
- 완료 기준: 오프라인에서도 업로드→요약→체크리스트→리포트가 끊김 없이 시연된다.

**우선순위 원칙**: "결정론 파이프라인 → 프론트 연동 → LLM 서술" 순서. LLM은 마지막에 얹어도 시스템 가치가 성립하도록 배치(리스크 후행).

---

## 부록. 후속 리뷰(2·3번 과제) 연결

- 본 설계의 `rules/`(모듈=룰, `RULES` 리스트) + `services/validation_engine.py` 구조는 **2번 과제(아키텍처 리뷰)** 기준 5개(독립 테스트성·결정론·ValidationIssue 프론트 적합성·룰 확장성·복잡도)에 그대로 대응하도록 잡았다.
- README·역할분리·테스트 커버리지·데모 안정성(fallback)은 **3번 과제(포트폴리오 리뷰)** 기준에 대응. 구현 완료 후 2·3번 리뷰를 실코드 대상으로 수행한다.
