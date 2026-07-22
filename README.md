# 발주맞춤 · OrderFit — 매장 맞춤 재발주점

> **⚠️ ARCHIVED · 공식 마감 (2026-07-22)**  
> `pivot/project-direction` 피벗 개발을 포함한 본 프로젝트는 **2026-07-22** 부로 공식적으로 종료되었습니다.  
> GitHub **public archive** 로 동결합니다. 이슈·PR·추가 커밋은 받지 않습니다.  
> 시연 URL·로컬 실행은 참고용이며, 운영 지원은 없습니다.

> **제품명**: **발주맞춤** (EN: **OrderFit**) — 자영업·현업을 위한 재발주점(ROP)·발주량 가이드  
> **상태**: 매장·상권 파라미터 → 내부 점수·KB 매칭 → **ROP·안전재고·발주 레버 리포트** (동결)  
> **LT**는 품목 계약/표준 입력으로 **유지**(출력에서 변동 추천 없음) · 물류 리스크는 **버퍼 재고**로 전환  
> **코드/레포 이력명**: `md-preflight` (v1 프로모션 사전검수 아카이브 유지)  
> **활성 브랜치(마감 시점)**: `pivot/project-direction` · **v1 동결**: `main` @ tag `archive/v1-md-preflight`  
> **v1** (프로모션 사전검수): [`archive/v1-md-preflight/`](archive/v1-md-preflight/) · 태그 `archive/v1-md-preflight`  
> **기간**: 2026-07-02 ~ 2026-07-22

FastAPI · Pydantic · 모듈형 3단 파이프라인

자세한 마감 기록: [`ARCHIVE.md`](ARCHIVE.md)

---

## 무엇을 하는가

운영 중인 매장 정보와 재고 최적화 대상 품목을 입력하면:

1. **입력** — 유형·규모·객단가·행정동·상권·접근성·일평균 소진량 (및 선택적 표준 LT/ROP·서비스 레벨·발주 패턴)  
2. **내부 연산** — 물류 CAPA·수요 변동 가중치 + KB 매칭 → **고정 LT** 기준 ROP / SS / 1회 발주량 / 요일  
3. **출력** — 표준 대비 비교 대시보드 + 근거 블록 리포트  

유형과 규모/객단가가 어긋나면 **규모·객단가 선택값**을 연산 기준으로 쓰고 안내 문구를 띄웁니다.  
공식 정본: [`docs/redesign/pipeline.md`](docs/redesign/pipeline.md).

---

## 빠른 시작

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000
```

**라이브 (제3자 시연)**: [https://baljumatch.vercel.app](https://baljumatch.vercel.app)

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

### 제3자 시연 체크

1. 브라우저에서 라이브 URL 또는 로컬 `http://127.0.0.1:8000` 을 연다.  
2. 환영 화면 **시연 시나리오** 카드에서  
   - **좁은 편의점 · CAPA** → 다회 소량·상한  
   - **대형마트** → 채널 체급 비교  
   - **상세 주소 · 일시 유동** → Kakao POI·행사 수요 증분 (키 없으면 fallback 200)  
   - **유형·규모 불일치** → guidance 배너  
3. 결과에서 **쉬운 설명 / 전문 해설** 토글 · **리포트 내보내기**(PDF·MD·CSV·JSON).  
4. API·정적 자산 일괄 스모크:

```bash
./demo.sh            # local :8000
./demo.sh --prod     # production
```

검증:

```bash
uv run ruff check app tests
uv run basedpyright app
uv run pytest
node scripts/verify_wizard_logic.mjs
node scripts/verify_report_export.mjs
node scripts/verify_demo_scenarios.mjs
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

## 산출 근거 (시연·평가)

공식 항별 문헌·가정 매핑: **[`docs/evidence/`](docs/evidence/)**  
- 3층: L1 표준 이론 · L2 King/APICS·ASCM·Huff · L3 engineering proxy  
- 시연 스코프(매장2·품목2): `docs/evidence/demo-scope.md`

---

## 문서

| 문서 | 경로 |
|------|------|
| **파이프라인 공식 정본** | [`docs/redesign/pipeline.md`](docs/redesign/pipeline.md) |
| **발표 Critic Q&A** | [`docs/redesign/critic-qa.md`](docs/redesign/critic-qa.md) |
| 아키텍처 요약 | [`docs/architecture.md`](docs/architecture.md) |
| 서비스 플로우 | `2026-07-14-New-Service-Flow.md` |
| 재설계 판 | `docs/redesign/` |
| 개발 일지 | `docs/dev-journal-2026-07.md` |
| v1 아카이브 | `archive/v1-md-preflight/` |
