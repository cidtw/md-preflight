# Tech Lead 진단 · 계약 동결 · 작업 분해 (재개용 핸드오프)

> 작성: 2026-07-04 · 역할: Claude = Tech Lead/아키텍처 리뷰어 · 상태: **진단·분해 완료, 구현 미착수**
> 이 노트만 읽으면 다음 세션에서 바로 업무 속행 가능하도록 작성함.

## 0. 이번 세션에서 한 일 (요약)
1. repo 전체 진단 + `uv run pytest` 확인(**17 passed**).
2. 문서 ↔ 코드 불일치, 위험요소, 포트폴리오 어필포인트 정리.
3. 되돌리기 어려운 아키텍처 결정 2건 **사용자 확인받아 동결**(아래 §2).
4. Codex 티켓 T1~T4 발행 + Gemini 검토 요청서 발행 (`handoff/tickets/`).
5. 진단 도중 **중대한 사실 정정**: antigravity 중복본은 별개 프로젝트가 아니라 submodule(§3).

## 1. 현재 코드 상태 (사실 기반)
- **완성도 높음(유지)**: 8개 룰 전부 구현·순수함수·예외격리(`failed_rules`), ingest(loader/normalize)·스키마(`ValidationIssue`/`PreflightReport`)·룰 유닛테스트(17 pass, 네트워크 無)·인메모리 `RunStore`.
- **비어있음(핵심 공백)**:
  - **실제 LLM 서술 미구현** — `app/services/llm_service.py`는 fallback 템플릿만. `generated_by`는 항상 `"fallback"` 하드코딩. anthropic 호출·프롬프트·JSON 스키마 전무.
  - `POST /api/preflight`(전체 파이프라인) 없음 — `/validate`(룰만)만 존재.
  - `report_service.render_markdown_report()`는 구현됐으나 **어떤 엔드포인트에도 미연결(dead code)**. PDF 없음.
  - README 스텁, 프론트/데모 없음.
- **코드 냄새(사소)**: `app/rules/margin_rate.py`의 `int(str(row.source_row))`/`float(str(row.promo_price))` 재캐스팅 — 불필요, 의도 주석 필요.

## 2. 동결된 아키텍처 결정 (사용자 확인 완료)
- **D1 정본 = `projects/md-preflight`.** (antigravity 쪽은 §3 참고 — 단순 archive 아님)
- **D2 API 계약 = 코드 경로 유지 + 문서를 코드에 맞춤.** 정본 경로:
  - `POST /api/preflight/validate` (룰만, 기존)
  - `POST /api/preflight` (전체, `use_llm`) — **T2 신규**
  - `GET /api/preflight/runs/{run_id}`
  - `GET /api/preflight/runs/{run_id}/report.md` — **T3 신규**
  - `GET /api/preflight/rules`
  - `GET /api/preflight/health`
- **D3 LLM 경계**: 입력=확정된 `PreflightSummary`+`issues`, 출력=`{ai_summary, checklist}` JSON 강제, 프롬프트에 "재판단·새 이슈 생성 금지" 명시, 실패 시 fallback+`generated_by="fallback"`.
- **D4 `use_llm: bool=true`** 플래그(false면 fallback 강제, 오프라인 데모). **D5 모델 `claude-sonnet-5`, temp 낮게, JSON 스키마.** **D6 리포트: md=MVP, pdf=P2.**

## 3. ⚠️ 중대 정정 — 중복본의 실체
- `projects/md-preflight`와 `projects/antigravity/md-preflight`는 **다른 프로젝트가 아니라 같은 GitHub 레포(`github.com/cidtw/md-preflight.git`)의 두 워킹카피**.
- `projects/antigravity/md-preflight`는 antigravity 상위 레포의 **git submodule**이며 초기 커밋 `5050e23`에 pin됨(stale).
- "antigravity가 구버전"인 진짜 이유 = **정본의 최신 작업이 아직 커밋/푸시 안 됨 → 워킹트리에만 존재(소실 위험).**
- 따라서 submodule을 `mv`/`rm`으로 옮기면 상위 레포 참조 파손. **T1은 "미커밋 작업 커밋/푸시 → submodule update --remote(A안) 또는 deinit(B안)" 순서.**

## 4. 발행된 산출물 (이 디렉토리)
```
handoff/tickets/
├─ README.md                     # 티켓 인덱스 + 동결 API 계약 + 공통 규칙(검증 3종)
├─ T1-commit-and-submodule.md    # P0 미커밋 보존 + 서브모듈 정리 (최우선)
├─ T2-post-preflight-endpoint.md # P0 POST /api/preflight (+use_llm 자리예약)
├─ T3-report-md-endpoint.md      # P1 report.md 다운로드 배선
├─ T4-doc-sync.md                # P0 BACKEND_ARCHITECTURE.md 정합화(문서만)
└─ GEMINI-review-request.md      # Gemini 감사 요청서 (G-1~G-4)
```
- 권장 착수 순서: **T1 → T4 → T2 → T3.**
- 각 티켓 공통 완료조건: `uv run ruff check app tests` + `uv run basedpyright app tests` + `uv run pytest` 통과 후 핸드오프 노트 작성.

## 5. 아직 안 한 것 / 다음 지시 대기 (재개 시 여기서 시작)
사용자 지시로 **여기서 중단**. 별도 지시 전까지 아래 미착수:
- **T5~T9 티켓 미발행**: T5(LLM 인터페이스 정의) / T6(anthropic 실제 호출+JSON 파싱) / T7(`use_llm` 배선+`generated_by` 정확화) / T8(LLM 결정론 계약 테스트) / T9(에러 규약 400/413).
- **실제 구현 착수 안 함** (모든 티켓 TODO 상태).
- README 재작성 안 함.

### 재개 시 추천 진입점
1. 사용자가 "구현 시작" 지시하면 → **T1부터** (미커밋 작업 보존이 최우선, 소실 위험).
2. "LLM 설계 파고들기" 지시하면 → T6 상세 설계(프롬프트 규약·JSON 스키마·목킹 전략) 먼저.
3. "T5~T9 티켓 마저 써라" → `handoff/tickets/`에 동일 형식으로 발행.

## 6. 역할 분담 (참고)
Claude=Tech Lead(설계/리뷰/통합) · Codex=티켓 구현(T1~T9) · Gemini=대조감사(GEMINI-review-request.md) · ChatGPT=README 문구/도메인 카피.
