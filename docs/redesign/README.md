# 재설계 — 매장 특화 ROP 서비스

> **브랜치**: `pivot/project-direction`  
> **지시**: `2026-07-14-Project-Redesign.md` · `2026-07-14-New-Service-Flow.md`

## 한 줄

운영 매장 정보와 품목 소진량을 받아 **Lead Time / Re-Order Point 재조정값**과 **근거 리포트**를 낸다.

## 문서

| 파일 | 내용 |
|------|------|
| [**`../architecture.md`**](../architecture.md) | **리빌드 아키텍처 요약 (정본)** |
| [`direction.md`](./direction.md) | 문제·원칙·비목표 |
| [`pipeline.md`](./pipeline.md) | 3단 계약·공식 |
| [**`critic-qa.md`**](./critic-qa.md) | **발표용 Critic Q&A 1페이지** |
| [**`../evidence/`**](../evidence/) | **산출 근거 패키지** (문헌·매트릭스·시연 스코프) |
| [`board.md`](./board.md) | 티켓 보드 |
| [`../dev-journal-2026-07.md`](../dev-journal-2026-07.md) | 개발 일지 |

## 코드 진입점

- `app/pipeline/runner.py`
- `POST /api/evaluate`
- UI: `/` (폼 → 로딩 → 리포트)
