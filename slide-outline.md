# 매장 특화 ROP 재조정 — 최종 발표 장표 (기초 아웃라인)

> **slides-grab Stage 1 (Plan / foundation)**  
> 본 문서는 **내용·구성·메시지 정본**이다. `slide-*.html` 재생성·디자인 게이트·PDF export는 **본 아웃라인 승인 후** Stage 2로 진행한다.  
> 근거: `docs/dev-journal-2026-07.md` (국면 I–IX) · `docs/architecture.md` · `docs/redesign/pipeline.md` · pivot tip `468e00d`

## Meta
- **Topic**: main v1(프로모션 사전검수) → 중간발표·피드백 → pivot ROP 제품 → 정확도·안정화·일시 유동까지 포함한 최종 산출
- **Target Audience**: 유통 비즈니스 이해관계자 · 테크 리드 · 멘토/평가 패널
- **Tone/Mood**: Restrained · Professional · Evidence-first (숫자·계약·데모 중심)
- **Slide Count**: **14 slides**
- **Aspect Ratio**: 16:9
- **Presentation focus**: 피벗 이유 + 동작하는 ROP 서비스 + 공식 정합 + 7/16 안정화·일시 유동 + 라이브 데모
- **Style (유지)**: `executive-minimal`  
  - 여백·키노트형 · 슬라이드당 한 메시지 · 비즈니스+기술 혼성  
  - 미채택: `ppt-consulting-precision-grid` · `swiss-international-style`  
  - 이전 중간발표 참고: `ppt-samsung-ir-restrained` (구 7장)
- **Branch policy**: **`main` = v1 아카이브 (변경 금지)** · 활성 개발·배포 = `pivot/project-direction`
- **Prod**: https://md-preflight.vercel.app
- **Status**: **STAGE 1 REVISED (2026-07-16)** — 내용 정본 갱신 완료 · Stage 2 HTML 재생성 **승인 대기**  
  (기존 `slides/slide-01..07.html` 은 구 아웃라인 잔존 — **재생성 대상**)

## Narrative Arc (한 줄)

```
문제(프로모션 오입력) → v1 라이브 검수 엔진 → 중간발표 피드백
  → 방향 피벗 → 매장 특화 ROP · 운영 레버
  → 정확도 패치(SS∝D) → 안정화·윤문·export
  → 일시 유동 수요 증분 → 라이브 · 다음
```

## Slide Composition

### Slide 1 - Cover
- **Type**: Cover
- **Title**: 매장 특화 발주 기준 재조정
- **Subtitle**: MD Preflight — v1 사전검수에서 ROP 운영 레버 제품까지
- **Kicker**: 2026.07.01–16 · main 아카이브 → pivot/project-direction · 라이브
- **Presenter**: 개발 권태원 (SaaS Platformer)
- **Notes**: 부제 한 줄 가능 — “Lead Time 입력 유지 · ROP·SS·Q·요일·SL 조정 · (선택) 일시 유동”

### Slide 2 - Agenda
- **Type**: Contents
- **Items**:
  1. 문제와 v1 해법 (`main`)
  2. 중간발표 성과와 한계 → 피벗
  3. 새 제품: 매장 특화 ROP
  4. 아키텍처 · 공식 · 지도·일시 유동
  5. 정확도·안정화 패치 (7/15–16)
  6. 검증 수치 · 데모 · 로드맵

### Slide 3 - 문제 정의 (유통 현장)
- **Type**: Content
- **Key Message**: 평균 표준 발주 기준으로는 매장마다 품절·과잉이 갈린다.
- **Details**:
  - **v1 문제**: 프로모션 등록 전 가격·기간·마진·재고 교차 오류 → 점포 혼선·마진 악화
  - **피벗 후 문제**: 업계·사내 평균 LT/ROP는 채널 평균에 가깝고, **입지·상권·CAPA·피크·(선택) 임시 유동**을 반영하지 못함
  - **제약**: 리드타임은 계약·품목 일정 → **「LT를 올려라」는 운영 레버가 아님**
- **Visual**: 좌 문제 카드 2장 (v1 / pivot) · 우 “고정 입력 vs 조정 레버”

### Slide 4 - v1 성과 스냅샷 (`main` 아카이브)
- **Type**: Statistics
- **Key Message**: 7/1–7/13, 결정론 검수 엔진을 라이브 SaaS까지 올렸다.
- **Details**:
  - **10룰** 결정론 판정 · LLM은 **서술만** (계약 테스트로 경계 고정)
  - **SPA 워크스페이스**: 업로드 → 이슈 → CSV 수정 → 재검수
  - **프로덕션**: Vercel · Clerk · Neon · OpenAI/Anthropic fallback
  - **품질 KPI**: pytest **132 → 150** (T59 피크)
  - **동결**: 태그 `archive/v1-md-preflight` @ `b444be0` · **이후 main 변경 없음**
- **Chart (optional)**: 막대 — pytest 47 → 104 → 132 → 150 (일지 §2)
- **Notes**: 티켓 T1–T59는 성과 스냅샷만; 전수 나열 금지

### Slide 5 - 중간발표 피드백 → 피벗
- **Type**: Content / Two-column
- **Key Message**: 피드백은 “더 많은 룰”이 아니라 **문제 정의 재정렬**을 요구했다.
- **Details**:
  - **유지**: 결정론 코어 · 근거 제시 · degrade 가능한 주변부
  - **내려놓음**: 고정 스키마 프로모션 파일 검수 UI 복잡도
  - **새 목표**: 매장 파라미터 → 내부 점수 + KB → **근거 있는 발주 기준 추천**
  - **브랜치**: `main` 동결 · `pivot/project-direction` 3단 파이프라인 재구축
- **Visual**: Before/After (Preflight 검수 → ROP Adjust)

### Slide 6 - 제품 한 장 (What it does)
- **Type**: Content
- **Key Message**: 3세션 입력 → 내부 연산 → 비교 대시보드 + 근거 리포트 + 내보내기.
- **Details**:
  - **입력 (세션)**: ① 유형·규모·객단가 ② 행정동·**(선택) 상세주소**·상권·접근성·**일시 유동 옵션** ③ 품목·D·LT·SL·요일·표준 ROP
  - **출력 레버**: ROP · 안전재고 · Q · 발주 요일/주기 · 서비스 레벨 Z  
  - **비레버**: LT — **입력 유지, 추천 변동 없음**
  - **UX**: 위저드 → 로딩 → 리포트 · **일반/전문 해설 토글** · **PDF·MD·CSV·JSON 내보내기**
  - **라이브**: https://md-preflight.vercel.app
- **Visual**: 3단 플로우 Input → Analyze → Output + 작은 “export / dual narrative” 칩

### Slide 7 - 아키텍처 (3단 파이프라인)
- **Type**: Content / Diagram
- **Key Message**: 스테이지를 늘 확장하고, 판정은 결정론으로 유지한다.
- **Details**:
  - **input/** 템플릿·검증 · 유형↔규모/객단가 불일치 시 **규모·객단가 우선** + guidance
  - **analyze/** scoring · Kakao Local geo · **event 200m 스캔(옵션)** · KB · engine
  - **output/** 한 줄 recommendation(plain+technical) · 비교표 · 근거 4블록 · guidance
  - **API**: `GET /api/template` · `POST /api/evaluate` · `GET /api/health`
- **Visual**: tldraw 권장 — 모듈 박스 + 데이터 화살표 (Stage 2)
- **Notes**: v1의 path 격리 교훈 → 주변부 최소, 코어 결정론

### Slide 8 - 핵심 공식 (운영 레버 · SS∝D)
- **Type**: Content
- **Key Message**: LT는 곱하는 상수, 조정은 재고·발주 정책으로 한다. 통계 SS는 **수요 비례**.
- **Details** (SSOT: `docs/redesign/pipeline.md`):
  - `LT = 품목 표준/계약 입력` (출력 delta = 0) · 미입력 시 **규모 밴드→채널** 기본값
  - `Z = Z_policy(90/95/99) + 맥락(변동성·품목·FTI_kb)`
  - `buffer = D_eff × risk_days`
  - `SS_stat = Z × D_eff × √(LT × vol/5) × turnover` ← **∝ demand**
  - `SS = SS_stat + buffer` · `ROP = D_eff × LT + SS`
  - `Q ≈ D_eff × cycle` · CAPA 협소 시 MaxCap · **표시 SS 항등 유지** · Q ≤ MaxCap
  - 비교 표: 표준 SS/Q는 **행사 미반영 D** 기준 · 추천은 D_eff
- **Visual**: 공식 카드 4장 (LT · Z · SS∝D · ROP) + CAPA 칩
- **Do not invent numbers**: 데모 시 실 evaluate 응답

### Slide 9 - 지도 유동 · 일시 유동 옵션
- **Type**: Content / Two-column
- **Key Message**: 상세 주소가 있으면 구조 유동(POI)과 **임시 유동(행사 시설)** 을 나눈다.
- **Details**:
  - **구조 FTI (항상, 주소 시)**: 반경(기본 500m) POI · soft_sat · 카테고리 N캡 · CS2 저가중 · 실패 시 행정동 fallback
  - **일시 유동 (옵션)**: `consider_temp_foot_traffic` — **정확한 주소 필수** · **반경 200m**  
    경기장·공연장·전시장·컨벤션 키워드 → kind×거리×rank 가중 → uplift  
    `D_eff = D × (1 + 0.35×uplift)` (최대 약 +35%) · FTI에 uplift 블렌드
  - **한계**: 실시간 행사 캘린더 없음 → **대형 유동 가능 시설 근접 프록시** (근거 블록에 명시)
- **Visual**: 좌 구조 POI 원(500m) · 우 행사 스캔 원(200m) · 수요 배수 바

### Slide 10 - 정확도·안정화 패치 (7/15–16)
- **Type**: Content
- **Key Message**: 리뷰·현장 피드백으로 **틀린 숫자와 안 열리는 버튼**을 먼저 막았다.
- **Details**:
  - **VIII (7/15)**: SS∝D · 비교표 Z/주기 기준 · size 기본값 · geo FTI 귀속 · CAPA 표시 SS
  - **IX (7/16)**:
    - CAPA **Q ≤ MaxCap** (저수요 floor 버그 제거)
    - Q-only multi-order 시 CAPA 문구 「무리 없이」 제거
    - 추천 한 줄 **문장형 윤문** (일반·전공)
    - **리포트 내보내기** 복구 (result-panel 이벤트 위임)
    - 일시 유동 옵션 · dual narrative · export 유지
- **Visual**: 타임라인 카드 “VIII 정확도 → IX 안정화·기능” · 커밋 칩 (ebe68f0…468e00d)

### Slide 11 - 검증 · 품질 · 지표 궤적
- **Type**: Statistics / Timeline
- **Key Message**: 제품이 바뀌어도 “측정 가능한 품질” 습관은 유지했다.
- **Details**:
  - **v1 peak**: pytest **150**
  - **pivot skeleton**: **12** (의도적 슬림)
  - **ROP + ops (7/14–15)**: **30 → 32**
  - **현행 (7/16 tip)**: **46** · ruff · basedpyright 0 · wizard/export node smoke
  - 계약: 결정론 · 예시 문장 하드코딩 금지 · LT 미조정 · ROP=D_eff×LT+SS 항등
- **Chart**: 라인/막대 — pytest 시점별 (일지 수치만; 창작 금지)

### Slide 12 - 데모 스토리보드
- **Type**: Timeline / Steps
- **Key Message**: 3–4분 안에 “입력 → 레버 → 근거 → 내보내기”를 보여 준다.
- **Details**:
  1. 세션1–3: 편의점 소형 · 오피스 · 건물 내 · 냉장 간편식 · D=12 · LT=2 · SL=95% · 요일=자동
  2. 결과: **문장형 추천** · ROP·SS·요일 · “배송 일정 그대로” 확인
  3. **전문 해설 토글** → Z·CAPA·공식 톤 전환
  4. (선택) 정확한 위치 + **일시 유동** 체크 → geo/행사 근거 · D_eff 언급
  5. **리포트 내보내기** → PDF/MD 중 하나
- **Notes**: Kakao 키 없을 때 fallback도 의도된 UX로 설명 · 하드 리프레시 후 export

### Slide 13 - 로드맵 · 의사결정
- **Type**: Content
- **Key Message**: 다음은 “더 예쁜 UI”보다 **실측 데이터와 운영 연동**.
- **Details**:
  - **DONE (부분)**: Vercel prod 반복 배포 · trust 카피 · export · 일시 유동 프록시
  - **NEXT**: 실시간 행사 캘린더/공공 API · 실측 KB · Agent 포트 · 품목 마스터 · 발주 캘린더 UX · evaluate 취소 UX
  - **비목표**: main 부활 · v1 프로모션 검수 UI 복원 (태그로만)
- **Visual**: Now / Next / Later 3열

### Slide 14 - Closing · Q&A
- **Type**: Closing
- **Message**:  
  v1으로 **신뢰 가능한 결정론 제품** 습관을 만들었고,  
  피벗 후 **매장이 실제로 움직이는 발주 레버**에 그 습관을 옮겼습니다.  
  7/16까지 **정확도·문장·내보내기·일시 유동**까지 프로덕션에 올렸습니다.
- **Contact**: GitHub `github.com/cidtw/md-preflight` · 브랜치 `pivot/project-direction` · https://md-preflight.vercel.app
- **Appendix pointers**: `docs/dev-journal-2026-07.md` · `docs/architecture.md` · `docs/redesign/pipeline.md`

---

## Style decision

| 항목 | 값 |
|------|-----|
| **확정** | `executive-minimal` (기존 유지) |
| **선정 이유** | 14장 스토리 아크를 슬라이드당 한 메시지로 · 비즈니스+기술 혼성 |
| **Design note** | 표·공식은 카드 2–4개 · 다이어그램 단순 3단 · Chart.js는 지표 슬라이드 1장 · 행사 슬라이드는 이중 반경 시각 |
| **미채택** | consulting-precision-grid · swiss |

**Stage 2 진입 조건**: 본 14장 문구·순서 승인 후 `slides-grab-design`으로 `slides/slide-01..14.html` **전량 재생성** (구 7장 HTML 폐기/교체).

## Source map (사실 출처)

| 슬라이드 | 출처 |
|----------|------|
| 4 v1 성과 | `docs/dev-journal-2026-07.md` §0–3 · tag archive |
| 5 피벗 | `2026-07-14-Project-Redesign.md` · redesign/ |
| 6–8 제품·공식 | `docs/redesign/pipeline.md` · `docs/architecture.md` |
| 9 Kakao·event | `docs/setup-kakao-local.md` · `geo_enrichment.py` · `event_foot_traffic.py` |
| 10 패치 | 일지 국면 VIII–IX · 커밋 ebe68f0…468e00d |
| 11 지표 | 일지 · pytest **46** (2026-07-16 tip) |
| 12 데모 | `POST /api/evaluate` · 라이브 URL |
| 13 로드맵 | 일지 「이후 — ROP 고도화」 |

## Out of scope (이번 아웃라인 / Stage 1)

- `slide-*.html` 자동 생성·디자인 게이트·PDF (승인 후 Stage 2–3)
- 미검증 비즈니스 ROI 수치 창작
- v1 전 티켓 T1–T59 전수 나열
- main 브랜치 기능 재개

## Stage 2 체크리스트 (승인 후)

1. `slides-grab-design` — `style: executive-minimal` · 14장 HTML  
2. `slides-grab validate --slides-dir slides`  
3. Design gate (Pass A/B) · Critical 0  
4. 사용자 편집 승인 → `slides-grab pdf` (또는 PNG)
