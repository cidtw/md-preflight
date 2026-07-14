# Archive — v1 MD Preflight (프로모션 사전검수)

> **상태**: 아카이브 (활성 제품 경로 아님)  
> **일자**: 2026-07-14  
> **사유**: 프로젝트 방향성 재설정 (`2026-07-14-Project-Redesign.md`)  
> **Git 태그**: `archive/v1-md-preflight`  
> **복원**: 아래 *RESTORE* 참고

## 한 줄

유통 프로모션 등록 전 Excel/CSV 3파일을 결정론 룰 엔진으로 검수하고, LLM은 서술만 담당하던 **v1 제품 전체**를 동결·보관한다.

## 왜 아카이브했는가

1. **기능 과다** — 10룰 엔진 + 멀티시트 어댑터 + 역할 매핑 + SPA 편집기 + 이력/Clerk/Neon + 설정 카탈로그 등 표면이 비대해짐  
2. **서비스 근거 빈약** — “왜 이 서비스인가”를 뒷받침할 조사·가중치·추천 논리가 제품 중심에 없음  
3. **가벼운 서비스 + 무거운 웹 표준** — 핵심 가치가 얇은데 프론트/인증/영속 경로가 사이트 체감을 무겁게 만듦  

재설계 방향은 **좁은 스코프 · 파라미터 입력 · 사전 조사된 평가 가중치 · 한 줄 recommendation · 모듈형 3단 파이프라인**이다.  
세부 서비스 구성은 준비 과정(아카이브 → 파이프라인 재편 → 판 제작) 완료 후 진행한다.

## 동결 시점

| 항목 | 값 |
|------|-----|
| 태그 | `archive/v1-md-preflight` |
| 기준 브랜치 | `main` / 작업 브랜치 `pivot/project-direction` 분기 시점 |
| 커밋 | 태그 생성 시 HEAD (`git rev-list -n1 archive/v1-md-preflight`) |
| 참고 pytest | **150** (T58/T59 시점, 일지 기록) |

## 포함 범위 (요약)

| 영역 | 내용 |
|------|------|
| 판정 | 10개 결정론 룰 · `PreflightContext` · D3 계약 |
| 입력 | CSV/XLSX · 별칭 수렴 · 멀티시트 · N파일 역할 매핑 |
| 서술 | OpenAI/Anthropic + Fallback |
| 영속 | RunStore / HistoryStore (메모리·Postgres) |
| 인증 | Clerk / stub / off |
| UI | SPA (업로드·편집·이력·설정·테마 등) |
| 문서 | `BACKEND_ARCHITECTURE.md`, `DESIGN.md`, `docs/architecture-*.md`, ADR-0001, 개발일지 Part A–B |

상세 목록: [`MANIFEST.md`](./MANIFEST.md)  
폐기·격리 판단: [`DISCARD-REVIEW.md`](./DISCARD-REVIEW.md)

## 복원 (RESTORE)

전체 트리 확인:

```bash
git show archive/v1-md-preflight:README.md | head
git ls-tree -r --name-only archive/v1-md-preflight | head
```

특정 경로만 작업 트리로 꺼내기:

```bash
git checkout archive/v1-md-preflight -- app/rules app/ingest
```

태그 전체 체크아웃(읽기 전용 조사용 worktree 권장):

```bash
git worktree add /tmp/md-preflight-v1 archive/v1-md-preflight
```

## 관련 문서

- 재설계 지시: 저장소 루트 `2026-07-14-Project-Redesign.md`
- 재설계 판: `docs/redesign/`
- 개발 일지 정본: `docs/dev-journal-2026-07.md` (§0 국면 VI)
