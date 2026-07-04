# Codex 작업 티켓 (md-preflight)

Tech Lead(Claude)가 분해한 구현 티켓. 각 티켓은 콜드 스타트로 착수 가능한 자립형 지시서다.
정본 레포는 `projects/md-preflight`. 상위 antigravity 레포의 `md-preflight`는 같은 GitHub 레포(`cidtw/md-preflight.git`)의 submodule이며 초기 커밋에 고정된 stale 상태.

## 공통 규칙 (모든 티켓)
- 착수 전: `git status` 확인, `README.md`·`AGENTS.md`·`BACKEND_ARCHITECTURE.md` 읽기.
- 코어 디렉터리 이름 변경 금지. API 계약 변경 시 문서 동시 갱신.
- 완료 후 검증 3종 통과 필수:
  - `uv run ruff check app tests`
  - `uv run basedpyright app tests`
  - `uv run pytest`
- 완료 후 `handoff/YYYY-MM-DD-<summary>.md` 핸드오프 노트 작성.
- **한 티켓 = 한 관심사.** 범위 밖 파일은 건드리지 않는다.

## 동결된 API 계약 (정본)
| Method | Path | 설명 | 티켓 |
|--------|------|------|------|
| POST | `/api/preflight/validate` | 룰만 실행(LLM 생략) | 기존 |
| POST | `/api/preflight` | 전체 파이프라인 (`use_llm` 플래그) | T2 |
| GET | `/api/preflight/runs/{run_id}` | 저장된 결과 재조회 | 기존 |
| GET | `/api/preflight/runs/{run_id}/report.md` | Markdown 리포트 | T3 |
| GET | `/api/preflight/rules` | 룰 메타 목록 | 기존 |
| GET | `/api/preflight/health` | 헬스체크 | 기존 |

## 티켓 목록
| ID | 제목 | 상태 | 파일 |
|----|------|------|------|
| T1 | 미커밋 작업 보존 + 서브모듈 정리 | TODO | T1-commit-and-submodule.md |
| T2 | `POST /api/preflight` 추가 | TODO | T2-post-preflight-endpoint.md |
| T3 | Markdown 리포트 다운로드 엔드포인트 | TODO | T3-report-md-endpoint.md |
| T4 | BACKEND_ARCHITECTURE.md 코드 정합화 | TODO | T4-doc-sync.md |
| T5~T9 | (LLM 서술·플래그·계약 테스트·에러 규약) | 후속 발행 예정 | — |

## 권장 순서
T1 → T4 → T2 → T3 (T4 문서 동결 후 엔드포인트를 문서대로 구현). T5~T9는 T1~T4 완료 후 발행.
