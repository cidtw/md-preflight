# MD Preflight — Pipeline Redesign Skeleton

> **현재 브랜치 방향**: 파라미터 입력 → 가중치 분석 → **한 줄 recommendation**  
> **v1 (프로모션 사전검수)**: 아카이브됨 — [`archive/v1-md-preflight/`](archive/v1-md-preflight/) · 태그 `archive/v1-md-preflight`

FastAPI · Pydantic · 모듈형 3단 파이프라인

---

## 왜 재설계인가

1. 기능이 너무 많았고  
2. 서비스 근거의 조사·가중치가 약했으며  
3. 가벼운 본체에 비해 웹/프로덕션 표면이 무거웠다  

목표: **좁은 스코프**, **열린 파라미터 입력**, **사전 조사된 평가 가중치**, **명확한 한 줄 추천**, **모듈형 구조**.

세부 서비스 도메인은 준비 과정 완료 후 `docs/redesign/board.md`에서 진행한다.

---

## 파이프라인

```
parameters ──► [INPUT] template validate
                    │
                    ▼
              [ANALYZE] weighted criteria (deterministic)
                    │
                    ▼
              [OUTPUT] one-line recommendation + score breakdown
```

| Stage | Path |
|-------|------|
| Input | `app/pipeline/input/` |
| Analyze | `app/pipeline/analyze/` |
| Output | `app/pipeline/output/` |
| Runner | `app/pipeline/runner.py` |

---

## API

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/health` | 헬스 |
| `GET` | `/api/template` | 입력 파라미터 템플릿 |
| `POST` | `/api/evaluate` | 파이프라인 실행 |
| `GET` | `/` | 최소 UI 셸 |

### 예제

```bash
curl -s http://127.0.0.1:8000/api/template | jq .

curl -s -X POST http://127.0.0.1:8000/api/evaluate \
  -H 'content-type: application/json' \
  -d '{"parameters":{"quality":80,"cost":40,"risk":30}}' | jq .
```

---

## 로컬 실행

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

검증:

```bash
uv run ruff check app tests
uv run basedpyright app tests
uv run pytest
```

---

## 문서

| 문서 | 경로 |
|------|------|
| 재설계 지시 | `2026-07-14-Project-Redesign.md` |
| 재설계 판 | `docs/redesign/` |
| 개발 일지 | `docs/dev-journal-2026-07.md` |
| v1 아카이브 | `archive/v1-md-preflight/` |
| 브리프 | `PROJECT_BRIEF.md` |

---

## v1 복원

```bash
git worktree add /tmp/md-preflight-v1 archive/v1-md-preflight
# or
git checkout archive/v1-md-preflight -- app/rules
```
