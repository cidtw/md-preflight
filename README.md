# MD Preflight — 매장 특화 ROP 재조정

> **현재**: 매장·상권 파라미터 → 내부 점수·KB 매칭 → **Lead Time / ROP 추천 리포트**  
> **v1** (프로모션 사전검수): [`archive/v1-md-preflight/`](archive/v1-md-preflight/) · 태그 `archive/v1-md-preflight`

FastAPI · Pydantic · 모듈형 3단 파이프라인

---

## 무엇을 하는가

운영 중인 매장 정보와 재고 최적화 대상 품목을 입력하면:

1. **입력** — 유형·규모·객단가·행정동·상권·접근성·일평균 소진량 (및 선택적 표준 LT/ROP)  
2. **내부 연산** — 물류 CAPA·수요 변동 가중치 + 지식 베이스 매칭 → 추천 LT/ROP  
3. **출력** — 표준 대비 비교 대시보드 + 근거 3블록 리포트  

유형과 규모/객단가가 어긋나면 **규모·객단가 선택값**을 연산 기준으로 쓰고 안내 문구를 띄웁니다.

---

## 빠른 시작

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000
```

```bash
curl -s -X POST http://127.0.0.1:8000/api/evaluate \
  -H 'content-type: application/json' \
  -d '{
    "parameters": {
      "product_name": "냉장 간편식",
      "store_type": "convenience",
      "store_size": "cv_s",
      "avg_ticket": "t_le_8k",
      "location_dong": "서울시 마포구 서교동",
      "trade_area": "office",
      "accessibility": "indoor",
      "daily_demand": 12,
      "standard_lead_time_days": 2,
      "standard_rop": 15
    }
  }' | jq .recommendation
```

검증:

```bash
uv run ruff check app tests
uv run basedpyright app
uv run pytest
```

---

## 구조

```
app/pipeline/
  input/          # 템플릿·검증·불일치 안내
  analyze/        # scoring · knowledge_base · engine
  output/         # 비교표·근거 리포트
  runner.py
app/web/          # 폼 → 로딩 → 리포트
```

| API | 설명 |
|-----|------|
| `GET /api/health` | 헬스 |
| `GET /api/template` | 입력 템플릿 |
| `POST /api/evaluate` | ROP 재조정 실행 |

---

## 문서

| 문서 | 경로 |
|------|------|
| 서비스 플로우 | `2026-07-14-New-Service-Flow.md` |
| 재설계 판 | `docs/redesign/` |
| 개발 일지 | `docs/dev-journal-2026-07.md` |
| v1 아카이브 | `archive/v1-md-preflight/` |
