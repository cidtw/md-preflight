# 재설계 판 (Redesign Board)

> **브랜치**: `pivot/project-direction`  
> **지시문**: `2026-07-14-Project-Redesign.md`  
> **전제**: v1 아카이브 + 3단 파이프라인 스켈레톤 완료 후, **서비스 세부 구성**을 여기서 진행한다.

## 준비 과정 체크리스트

| # | 작업 | 상태 |
|---|------|------|
| 1 | main/v1 자료 백업·아카이브 (`archive/v1-md-preflight`, 태그 `archive/v1-md-preflight`) | DONE |
| 2 | 파이프라인 3단 재편 + 백엔드 keep/discard + 모듈 골격 | DONE |
| 3 | 재설계 판 제작 (본 디렉터리) | DONE |
| — | 서비스 세부 구성 (도메인·가중치 조사·UI) | **NOT STARTED** |

## 방향성 (확정)

1. 좁은 스코프, 논리·근거가 명확한 서비스  
2. 열린 입력: 누구나 **특정 파라미터**만 넣으면 → **사전 조사된 평가 가중치**로 분석 → **한 줄 recommendation**  
3. 명확한 프레임워크·간결 구조 → 환경 무관 동일 경험  
4. 블록·모듈형 → 이후 기능 추가 용이  

## 문서 맵

| 파일 | 내용 |
|------|------|
| [`direction.md`](./direction.md) | 문제·방향·비목표 |
| [`pipeline.md`](./pipeline.md) | 입력 템플릿 → 분석 → 출력 계약 |
| [`board.md`](./board.md) | 이후 작업 티켓 보드 |
| [`../dev-journal-2026-07.md`](../dev-journal-2026-07.md) | 개발 일지 정본 |

## 활성 코드 진입점

- 오케스트레이션: `app/pipeline/runner.py`
- API: `POST /api/evaluate`, `GET /api/template`, `GET /api/health`
- v1 복원: `archive/v1-md-preflight/README.md`
