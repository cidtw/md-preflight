# T2 — `POST /api/preflight` 전체 파이프라인 엔드포인트 추가

## 우선순위
P0. 현재는 룰만 도는 `POST /api/preflight/validate`만 있고, 설계 문서의 대표 엔드포인트 `POST /api/preflight`가 없다.

## 범위 파일
- `app/api/routes.py` (엔드포인트 추가)
- `tests/test_api.py` (테스트 추가)

## 배경
- 이 티켓 시점에는 LLM이 아직 미구현이다(`llm_service.py`는 fallback 템플릿만). 따라서 이 엔드포인트의 동작은 현재 `/validate`와 동일하게 fallback 서사를 반환한다.
- 단, **`use_llm` 파라미터를 지금 계약에 넣어 자리를 예약**한다. 실제 분기 배선은 후속 티켓 T7에서 한다. 이 티켓에서 `use_llm`은 받되 동작에 영향 없음(주석으로 명시).

## 구현 지시
1. `routes.py`에 핸들러 추가:
   - `@router.post("", response_model=PreflightReport)` (prefix가 `/api/preflight`이므로 빈 경로 = `POST /api/preflight`).
   - 3개 `UploadFile`(promotion_plan/product_master/inventory) + `use_llm: Annotated[bool, Form()] = True` + `run_store`/`settings` 의존성.
   - 기존 `validate_files`와 동일하게 `build_uploaded_context(...)` → `validate_context(context)` → `run_store.save(report)` → 반환.
   - `IngestError` → `HTTP 422` (기존 패턴 그대로 복제).
   - `use_llm`은 현재 미사용임을 코드 주석으로 남긴다: `# use_llm은 T7에서 배선. 현재는 항상 fallback.`
2. `fastapi`에서 `Form` import 추가.
3. 중복 로직이 커지면 `validate_files`와 공유 헬퍼로 뽑되, 과도한 추상화는 하지 말 것(현재 규모에선 소폭 중복 허용).

## 완료 기준
- `POST /api/preflight`에 정상 3파일 업로드 시 `200` + `PreflightReport` 스키마 반환.
- 저장되어 `GET /api/preflight/runs/{run_id}`로 재조회 가능.
- 컬럼 누락 파일 업로드 시 `422`.
- `GET /api/preflight/rules`, `/validate` 등 기존 엔드포인트 동작 불변.

## 테스트 기준 (`tests/test_api.py`)
- `test_post_preflight_returns_report`: 샘플 3파일 → 200, `PreflightReport.model_validate` 성공, `total_issues == 9`(기존 dirty 샘플 기준과 동일), `generated_by == "fallback"`.
- `test_post_preflight_missing_column_returns_422`: promotion에서 컬럼 하나 제거 → 422.
- `test_post_preflight_saved_run_is_retrievable`: 응답 `run_id`로 `GET /runs/{run_id}` → 200 동일 리포트.
- 실제 LLM/네트워크 호출 없음.

## 가드레일
- 룰 로직·스키마 변경 금지. 엔드포인트 추가만.
- `use_llm` 분기 구현 금지(T7 소관).
