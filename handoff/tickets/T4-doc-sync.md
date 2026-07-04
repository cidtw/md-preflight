# T4 — BACKEND_ARCHITECTURE.md 코드 정합화

## 우선순위
P0(문서 전용, 코드 변경 없음). 포트폴리오 리뷰어는 설계 문서를 계약으로 읽는다. 현재 문서와 실제 코드가 여러 곳에서 어긋나 있어 신뢰를 깎는다.

## 범위 파일
- `BACKEND_ARCHITECTURE.md` (문서만 수정)

## 배경
계약 동결 방침: **코드 경로를 정본으로 두고 문서를 코드에 맞춘다.** 아래 불일치를 문서 쪽에서 바로잡는다.

## 수정 항목 (체크리스트)
1. **§1 폴더 구조**
   - `tests/`는 중첩(`tests/rules/`, `tests/ingest/`, `fixtures/`)이 아니라 **flat 구조**다. 실제: `tests/conftest.py`, `tests/test_rules.py`, `tests/test_loader.py`, `tests/test_services.py`, `tests/test_api.py`. 문서를 이 구조로 교체.
   - 골든 샘플은 `tests/fixtures/`가 아니라 `data/samples/clean/`, `data/samples/dirty/`에 있다. 반영.
   - `services/llm_service.py`는 현재 **fallback 서사 전용**임을 명시(실제 LLM 호출은 후속 티켓 T6에서 추가 예정이라 주석).
2. **§4 API 설계 표** — 실제 라우터(`app/api/routes.py`, prefix `/api/preflight`)에 맞춰 경로 교체:
   | Method | Path | 비고 |
   |--------|------|------|
   | POST | `/api/preflight/validate` | 룰만 |
   | POST | `/api/preflight` | 전체(`use_llm`), T2에서 추가 |
   | GET | `/api/preflight/runs/{run_id}` | (문서의 `/api/preflight/{run_id}` 대체) |
   | GET | `/api/preflight/runs/{run_id}/report.md` | T3에서 추가 |
   | GET | `/api/preflight/rules` | (문서의 `/api/rules` 대체) |
   | GET | `/api/preflight/health` | (문서의 `/health` 대체) |
   - `report.pdf`는 아직 미구현 → "(계획, P2)"로 표기.
3. **§4 에러 규약** — 현재 코드가 처리하는 건 `422`(IngestError)와 개별 룰 예외 격리뿐이다. `413`/`400`은 **미구현**이므로 "(계획)"으로 명시하거나 후속 티켓 T9 참조로 표기.
4. **§2.4 / generated_by** — 현재 응답의 `generated_by`는 항상 `"fallback"`이며 `PreflightReport`에 `failed_rules: list[str]` 필드가 실제로 존재한다. 문서에 `failed_rules` 반영, `generated_by`는 "LLM 구현(T6) 전까지 fallback 고정"이라고 주석.
5. **§3.2 룰 표** — 실제 파일명과 대조: `date_range/product_master/promo_price/discount_rate/margin_rate/inventory/inbound_date/benefit_condition` 8개 모두 존재함을 확인하고 표의 severity·임계값이 코드(`RuleThresholds`: `max_discount_rate=0.7`, `min_margin_rate=0.05`)와 일치하는지 검수.

## 완료 기준
- 문서에 적힌 모든 API 경로가 `app/api/routes.py`에 실존한다(수동 1:1 대조).
- 폴더 구조·테스트 구조·에러 규약·`generated_by`/`failed_rules` 설명이 실제 코드와 일치.
- 아직 미구현인 항목은 "(계획)"으로 명확히 구분(허위 완성 표기 금지).

## 테스트 기준
- 코드 변경이 없으므로 pytest 영향 없음. `uv run pytest`가 여전히 통과하는지만 확인.
- 자체 검수: 문서의 경로 목록과 `grep -n '@router' app/api/routes.py` 결과를 대조한 표를 핸드오프 노트에 첨부.

## 가드레일
- 코드를 문서에 맞추려 하지 말 것(방향 반대). 이 티켓은 **문서만** 고친다.
- 미구현 기능을 구현된 것처럼 적지 말 것.
