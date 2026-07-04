# MVP Rule Expansion Handoff

## Summary
- 목적: 기대 디렉터리 구조를 보강하고 MVP 룰 구현 범위를 8개로 확장
- 결과: `docs/`, `outputs/` 경로를 추가하고 룰 엔진을 아키텍처 문서 기준 8개 룰로 확장

## Implemented
- 신규 룰 추가
  - `LOW_MARGIN_RATE`
  - `INVENTORY_SHORTAGE_RISK`
  - `INBOUND_DATE_CONFLICT`
  - `MISSING_BENEFIT_CONDITION`
- 서비스 분리
  - `app/services/llm_service.py`: fallback 요약/체크리스트 생성
  - `app/services/report_service.py`: Markdown 보고서 렌더링
- 설정 확장
  - `RuleThresholds.min_margin_rate` 추가
- 문서/구조 정렬
  - `docs/rule-matrix.md` 추가
  - `outputs/.gitkeep` 추가

## Validation
- `uv run ruff check app tests`
- `uv run basedpyright app tests`
- `uv run pytest`
- `TestClient`로 `/api/preflight/validate`, `/api/preflight/rules`, `/api/preflight/health` 호출 확인

## Notes
- 현재 `/api/preflight/rules`는 8개 룰을 반환
- 샘플 API 검증 입력 기준 총 9건 이슈가 발생
  - `LOW_MARGIN_RATE`가 경고 1건, 오류 승격 1건으로 2건 집계되기 때문
