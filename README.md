# MD Preflight

> 유통 프로모션 등록 **전에** 행사·상품·재고 파일을 검수해, 가격·기간·마진·재고·증정 조건의 운영 리스크를 사전에 잡아내는 도구.
> **핵심 원칙: 판단은 결정론적 규칙 엔진이, 서술만 LLM이 한다.**

FastAPI · Pandas · Pydantic · (선택) OpenAI / Anthropic

---

## 왜 이 프로젝트인가 — 문제

유통 프로모션은 가격, 기간, 재고, 입고일, 증정 조건, 마진, 종료 후 원복 등 여러 실행 요소가 동시에 맞아야 한다. 담당자(MD)의 작은 오입력 하나 — 행사가가 정상가보다 높거나, 시작일보다 입고일이 늦거나, 마진이 음수이거나 — 가 점포 혼선·고객 클레임·재고 부족·마진 악화로 번진다. **등록 버튼을 누르기 전에** 이 리스크를 자동 검수하는 것이 MD Preflight의 목적이다.

파일 3개(프로모션 계획 / 상품 마스터 / 재고)를 업로드하면 → 이슈 목록 · 요약 · 담당자 체크리스트 · Markdown 리포트를 돌려준다.

## 설계의 핵심 — 왜 판정을 LLM에 안 맡겼나

검수 판단(pass/fail)을 LLM에 맡기면 **비결정론·환각·감사 불가**라는 세 가지 문제가 생긴다. 같은 파일이 실행할 때마다 다른 결과를 낼 수 있고, "왜 이게 통과됐는가"를 설명할 수 없다. 운영·규제 도메인에서 이는 치명적이다.

그래서 이 프로젝트는 역할을 **엄격히 격리**한다.

```
                       ┌─ 판단(deterministic) ─┐   ┌─ 서술(LLM, 선택) ─┐
[3개 파일] → ingest →   │  rule engine          │ → │  요약 · 체크리스트  │ → PreflightReport
  업로드              │  10개 순수 함수 룰     │   │  (실패 시 fallback) │
                       │  → list[Issue] + 판정  │   └────────────────────┘
                       └────────────────────────┘
                        여기서 pass/fail 확정.       LLM은 이 확정된 사실을
                        LLM은 절대 개입 못 함.       "사람 말"로 바꿀 뿐.
```

- **결정론**: 같은 입력 → 항상 같은 이슈. 재현·감사 가능.
- **LLM은 판정선 밖**: LLM 생성기는 **이미 확정된 `summary`와 `issues`만** 입력받는다(타입으로 강제). 원본 셀 값·`product_name`은 프롬프트에 들어가지 않는다 → **프롬프트 주입으로 판정을 뒤집을 수 없음**(구조적 방어 + 계약 테스트로 증명).
- **데모는 안 죽는다**: LLM 키가 없거나 호출이 실패해도 결정론적 fallback 서사로 `200`을 반환한다. 응답의 `generated_by` 필드(`llm` / `fallback`)로 어느 경로였는지 투명하게 노출한다.

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

## 빠른 시작

```bash
uv sync
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

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

## API

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/preflight` | 전체 파이프라인. `use_llm`(기본 true) 폼 필드. |
| `POST` | `/api/preflight/validate` | 룰만 실행(LLM 생략, 항상 fallback) |
| `GET` | `/api/preflight/runs/{run_id}` | 저장된 결과 재조회 |
| `GET` | `/api/preflight/runs/{run_id}/report.md` | Markdown 리포트 다운로드 |
| `GET` | `/api/preflight/rules` | 룰 메타데이터 목록 |
| `GET` | `/api/preflight/health` | 헬스체크 |

**에러 규약**: 확장자 오류 `400` · 파일 크기 초과 `413` · 컬럼 누락/타입 오류 `422`. 개별 룰 예외는 500으로 새지 않고 격리되어 `failed_rules`에 담긴다.

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
uv run pytest            # 68 tests, 네트워크/실 LLM 호출 없음
```

- **CI에서 실제 LLM 호출 금지** — LLM 경로는 전부 목킹. `tests/test_narrative_contract.py`가 "LLM이 판정을 못 바꾼다"를 적대적으로 증명한다(악의적 서사·프롬프트 주입·범위 이탈 케이스).
- 골든 픽스처: `data/samples/clean`(passed) / `dirty`(10룰 전부) — 회귀 안전망 겸 데모 데이터.

## 범위 밖 (의도적 제외)

실시간 POS/ERP 연동, 수요예측. 3주 MVP 스코프를 통제하기 위한 명시적 제외다. 로그인은 검수 경로가 아니라 이력 대시보드에만 선택적으로 붙는다.

## 선택 로그인 · 이력 대시보드

- 검수 파이프라인은 **비로그인도 그대로 200**이다.
- `GET /api/preflight/history?granularity=day|month|year` 와 `GET /api/preflight/history/runs` 는 로그인 상태에서만 동작한다.
- 서버는 `CLERK_SECRET_KEY` 와 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 가 함께 설정되면 Clerk 세션 토큰(`Authorization: Bearer ...` 또는 `__session` 쿠키)을 검증해 실제 user ID를 얻는다. 이때 `aud` 대신 `iss` 와 `azp`(허용 origin 목록) 기준으로 검증한다.
- 두 키가 없으면 기존 스텁 경로(`X-MD-Preflight-User-Id` 헤더 / `md_preflight_user_id` 쿠키)로 자동 fallback 하므로 로컬 데모와 테스트는 계속 가볍게 유지된다.
- 이력 저장소는 `DATABASE_URL` 이 설정되면 Neon/Postgres `run_history` 테이블에 append/query 하고, 비설정 환경에서는 `InMemoryHistoryStore` 로 fallback 한다. 스토어 초기화가 실패해도 검수 요청은 메모리 스토어로 degrade 되어 200을 유지한다.

## 문서

- [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) — 문제 정의·설계 원칙
- [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md) — 아키텍처 설계안
- [`docs/rule-matrix.md`](docs/rule-matrix.md) — 룰 판정 매트릭스
