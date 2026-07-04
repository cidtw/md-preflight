# T3 — Markdown 리포트 다운로드 엔드포인트

## 우선순위
P1. `report_service.render_markdown_report()`는 이미 구현돼 있으나 **어떤 엔드포인트에도 연결되지 않았다**(dead code). 배선만 하면 데모 가치가 바로 생긴다.

## 범위 파일
- `app/api/routes.py` (엔드포인트 추가)
- `tests/test_api.py` (테스트 추가)

## 구현 지시
1. `routes.py`에 핸들러 추가:
   - `@router.get("/runs/{run_id}/report.md")`.
   - `run_store.get(run_id)` → `None`이면 `HTTP 404` (기존 `get_run` 패턴 복제).
   - 존재하면 `render_markdown_report(report)` 호출.
   - 응답은 `fastapi.responses.Response`(또는 `PlainTextResponse`)로 반환, `media_type="text/markdown; charset=utf-8"`.
   - 다운로드 UX를 위해 헤더 `Content-Disposition: attachment; filename="preflight-{run_id}.md"` 부여(선택이지만 권장).
2. import 추가: `from app.services.report_service import render_markdown_report`, `from fastapi.responses import Response`.
3. `response_model`은 지정하지 않는다(텍스트 응답이므로).

## 완료 기준
- 저장된 `run_id`에 대해 `GET /api/preflight/runs/{run_id}/report.md` → `200`, `Content-Type`이 `text/markdown` 계열, 본문에 `# MD Preflight Report`와 이슈 섹션 포함.
- 없는 `run_id` → `404`.
- 기존 엔드포인트 동작 불변.

## 테스트 기준 (`tests/test_api.py`)
- `test_report_md_download`: 샘플 업로드로 run 생성 → 그 `run_id`로 report.md 요청 → 200, `"# MD Preflight Report" in response.text`, `content-type`에 `markdown` 포함.
- `test_report_md_unknown_run_returns_404`: 임의 id → 404.

## 가드레일
- `render_markdown_report`의 렌더 로직은 이 티켓에서 바꾸지 않는다(배선만). 렌더 개선이 필요하면 별도 티켓.
- PDF는 이 티켓 범위 밖(후속 P2).
