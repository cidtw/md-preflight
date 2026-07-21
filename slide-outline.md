# 매장 특화 ROP 재조정 — 최종 발표 장표 (기초 아웃라인)

> **slides-grab Stage 1 (Plan / foundation)**  
> 본 문서는 **내용·구성·메시지 정본**이다. `slide-*.html` 재생성, 디자인 게이트, PDF export는 **본 아웃라인 승인 후** Stage 2로 진행한다.  
> 근거: `docs/dev-journal-2026-07.md` (국면 I–**XII**), `docs/architecture.md`, `docs/redesign/pipeline.md`, **`docs/evidence/`**, pivot

## Meta
- **Topic**: main v1(프로모션 사전검수) → 중간발표·피드백 → pivot ROP 제품 → 정확도·안정화 → 근거 심화 → **상권·시뮬·서사 정합**
- **Target Audience**: 유통 비즈니스 이해관계자, 테크 리드, 멘토/평가 패널
- **Tone/Mood**: Restrained · Professional · Evidence-first (숫자, 계약, 문헌, 데모 중심)
- **Slide Count**: **14 slides**
- **Aspect Ratio**: 16:9
- **Presentation focus**: 피벗 이유 + 동작하는 ROP + **L1–L3 근거** + 경쟁·what-if + 좁은 스코프 시연 + 로드맵
- **Style (유지)**: `executive-minimal`  
  - 여백·키노트형, 슬라이드당 한 메시지, 비즈니스+기술 혼성  
  - 미채택: `ppt-consulting-precision-grid`, `swiss-international-style`  
  - 이전 중간발표 참고: `ppt-samsung-ir-restrained` (구 7장)
- **Branch policy**: **`main` = v1 아카이브 (변경 금지)** · 활성 개발·배포 = `pivot/project-direction`
- **Prod**: https://baljumatch.vercel.app
- **Status**: **STAGE 2 DESIGN (2026-07-20)**: 윤문 아웃라인 기준 `slides/slide-01..14.html` 전량 재생성 · validate pass · design-gate Proceed
- **Quality tip (7/20)**: pytest **85** · ruff · basedpyright 0 · competition_sim smoke

## Narrative Arc (한 줄)

```
문제(프로모션 오입력) → v1 라이브 검수 엔진 → 중간발표 피드백
  → 방향 피벗 → 매장 특화 ROP · 운영 레버
  → 정확도·안정화·일시 유동
  → 튜터: 근거 빈약 우려 → 문헌 매트릭스 + 스코프 축소
  → 상권 경쟁·what-if · 식=서사 정합 → 라이브 · 다음(실측 교체)
```

## Slide Composition

### Slide 1 - Cover
- **Type**: Cover
- **Title**: 매장 특화 발주 기준 재조정
- **Subtitle**: 발주맞춤 · OrderFit: v1 사전검수에서 ROP, 근거, 상권 시뮬까지
- **Kicker**: 2026.07.01–20 · main 아카이브 → pivot/project-direction · 라이브
- **Presenter**: 개발 권태원 (SaaS Platformer)
- **Notes**: “Lead Time은 입력으로 유지합니다. 조정은 ROP, SS, Q, 요일, SL입니다. **근거 L1–L3**, **D_eff 정합**까지 맞춰 두었습니다.”

### Slide 2 - Agenda
- **Type**: Contents
- **Items**:
  1. 문제와 v1 해법 (`main`)
  2. 중간발표 → 피벗 → 튜터 피드백
  3. 새 제품: 매장 특화 ROP
  4. 아키텍처 · **공식 + 문헌 근거**
  5. 지도·경쟁·일시 유동 · 정확도 패치
  6. **좁은 스코프 데모** · what-if · 검증 · 로드맵

### Slide 3 - 문제 정의 (유통 현장)
- **Type**: Content
- **Key Message**: 평균 표준 발주 기준으로는 매장마다 품절과 과잉이 갈린다.
- **Details**:
  - **v1 문제**: 프로모션 등록 전 가격·기간·마진·재고가 서로 어긋나면 점포 혼선과 마진 악화로 이어짐
  - **피벗 후 문제**: 업계·사내 평균 LT/ROP는 채널 평균에 가깝고, **입지·상권·CAPA·피크·(선택) 임시 유동·경쟁**을 반영하지 못함
  - **제약**: 리드타임은 계약·품목 일정이다. 그래서 **「LT를 올려라」는 운영 레버가 아니다**
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
- **Chart (optional)**: 막대: pytest 47 → 104 → 132 → 150 (일지 §2)
- **Notes**: 티켓 T1–T59는 성과 스냅샷만. 전수 나열은 하지 않는다.

### Slide 5 - 피드백 두 단계 → 피벗 · 근거 심화
- **Type**: Content / Two-column
- **Key Message**: 중간발표는 **문제 정의**를, 튜터는 **논리와 객관 근거**를 요구했다.
- **Details**:
  - **중간발표 → 피벗**: 고정 스키마 검수 UI는 줄이고, 매장 특화 ROP 제품으로 옮김 (`pivot/project-direction`)
  - **유지**: 결정론 코어, 근거 제시, degrade 가능한 주변부
  - **튜터 (ROP 이후)**: 아이템(ROP·LT 레버·이중 UX)은 고평가. 다만 **산출의 객관 근거가 약해 보인다**는 우려
  - **수용**: 품목·매장 수를 줄여도 된다 → **논리 완결 우선** · `docs/evidence/`
  - **후속 (XII)**: 근거 표 위에 **경쟁·시뮬·숫자 서사 일치**까지 닫음
- **Visual**: 2단 타임라인: (1) 피벗 (2) 근거 심화 → (3) 정합

### Slide 6 - 제품 한 장 (What it does)
- **Type**: Content
- **Key Message**: 3세션 입력 → 내부 연산 → 비교 대시보드 + 근거 + **what-if** + 내보내기.
- **Details**:
  - **입력 (세션)**: ① 유형·규모·객단가 ② 행정동·**(선택) 상세주소**·상권·접근성·**일시 유동·경쟁 포화** ③ 품목·D·LT·SL·요일·표준 ROP
  - **출력 레버**: ROP, 안전재고, Q, 발주 요일/주기, 서비스 레벨 Z  
  - **비레버**: LT: **입력 유지, 추천으로 바꾸지 않음**
  - **UX**: 위저드 → 로딩 → 리포트 · **일반/전문 토글** · **경쟁 시뮬 패널** · **PDF·MD·CSV·JSON**
  - **데모**: 앵커 census 검증 점포 카드 (정규화 스냅샷)
  - **라이브**: https://baljumatch.vercel.app
- **Visual**: 3단 플로우 Input → Analyze → Output + “sim / export / dual narrative” 칩

### Slide 7 - 아키텍처 (3단 파이프라인)
- **Type**: Content / Diagram
- **Key Message**: 스테이지를 묶어 확장하고, 판정은 결정론으로 유지한다.
- **Details**:
  - **input/** 템플릿·검증. 유형과 규모/객단가가 어긋나면 **규모·객단가 우선** + guidance
  - **analyze/** scoring, Kakao geo, **event 200m**, **competition**, KB, engine, **simulate**
  - **output/** recommendation(plain+technical), 비교표, 근거, L1–L3, guidance
  - **API**: `GET /api/template` · `POST /api/evaluate` · `POST /api/simulate` · places/regions · health
- **Visual**: tldraw 권장: 모듈 박스 + 데이터 화살표 (Stage 2)
- **Notes**: v1에서 배운 path 격리 → 주변부는 최소, 코어는 결정론

### Slide 8 - 핵심 공식 + 근거 3층
- **Type**: Content
- **Key Message**: LT는 상수, 조정은 재고·발주. **식은 표준 이론, 계수는 출처 표, 서사는 엔진과 같다**.
- **Details** (SSOT: `docs/redesign/pipeline.md` · `docs/evidence/evidence-matrix.md`):
  - **L1 형태**: `ROP = D_eff×LT + SS` · `SS ∝ Z·√LT` · continuous review (King/ASCM/교재)
  - **D_eff**: `D × event_mult × competition_factor` (옵션 합성)
  - **L2 수치**: CSL 90/95/99 → Z **1.28 / 1.65 / 2.33** (King APICS 2011 Fig.2)
  - **구현식**:  
    `SS_stat = Z × D_eff × √(LT × vol/5) × turnover`  
    `buffer = D_eff × risk_days` · `SS = SS_stat + buffer`  
    LT 입력 고정 · CAPA 시 MaxCap · 항등 유지
  - **L3 proxy (정직)**: vol 1–5, 접근성 일수, soft-sat, 경쟁 intensity = engineering assumption  
    → 시연에서 “캘리브레이션이 아님”을 명시 · 상세는 `docs/evidence/`
- **Visual**: 공식 블록 + 옆 작은 3층 칩 (L1/L2/L3)
- **Do not invent numbers**: 데모 숫자는 실 evaluate 응답만

### Slide 9 - 지도 신호: 구조 · 일시 · 경쟁
- **Type**: Content / Three-column (or Two + footer)
- **Key Message**: 상세 주소가 있으면 **구조 유동, 임시 유동, 경쟁 포화**를 옵션으로 나눈다.
- **Details**:
  - **구조 FTI (주소 시)**: 반경(기본 500m) POI · soft_sat · 카테고리 N캡 · CS2 저가중 · 실패 시 행정동 fallback
  - **일시 유동 (옵션)**: 정확한 주소 · **200m** 행사 시설 프록시 → `D_eff` 상방 (최대 약 +35%)
  - **경쟁 포화 (옵션)**: 업종 반경 스캔 · intensity → demand factor (최대 약 −40%) · Huff 형태 감쇠
  - **한계**: 실시간 점유·행사 캘린더는 없다 → **근접 프록시** (근거 블록에 명시)
- **Visual**: 세 원(500m / 200m / 업종 r) · 수요 배수 바

### Slide 10 - 정확도·안정화 · 정합 패치 (7/15–20)
- **Type**: Content
- **Key Message**: 틀린 숫자, 안 열리는 버튼, **엔진과 서사 불일치**를 순서대로 막았다.
- **Details**:
  - **VIII (7/15)**: SS∝D · 비교표 Z/주기 · size 기본값 · geo FTI 귀속 · CAPA 표시 SS
  - **IX (7/16)**: CAPA Q≤MaxCap · 추천 윤문 · export 복구 · 일시 유동 옵션
  - **XII (7/20) P0**:
    - 시뮬 매출하락 **AI/폴백 패널 UI 노출**
    - 리포트 ROP/SS/버퍼 **D_eff 일치**
    - 경쟁 공세 시나리오는 **−28% 수요 이탈만** (포화 계수 이중 적용 금지)
    - census 분류기(프레시·IGA·무인·소음 POI) + 스냅샷 **91점**
- **Visual**: 타임라인 “VIII → IX → XII” · 칩 “식=서사”

### Slide 11 - 검증 · 품질 · 지표 궤적
- **Type**: Statistics / Timeline
- **Key Message**: 제품이 바뀌어도 “측정 가능한 품질” 습관은 유지했다.
- **Details**:
  - **v1 peak**: pytest **150**
  - **pivot skeleton**: **12** (의도적 슬림)
  - **ROP + ops (7/14–15)**: **30 → 32**
  - **IX (7/16)**: **46–47**
  - **현행 (7/20 tip)**: **85** · ruff · basedpyright 0 · wizard/export/**competition_sim** smoke
  - 계약: 결정론 · 예시 문장 하드코딩 금지 · LT 미조정 · ROP=D_eff×LT+SS 항등 · 시뮬 단일 쇼크
- **Chart**: 라인/막대: pytest 시점별 (일지 수치만. 창작 금지)

### Slide 12 - 데모 스토리보드 (스코프 축소 · 실측 · what-if)
- **Type**: Timeline / Steps
- **Key Message**: 매장·품목을 줄이고, **한 케이스의 논리 체인**을 끝까지 보여 준다.
- **Details** (SSOT: `docs/evidence/demo-scope.md` · evaluate 2026-07-19):
  1. **시나리오 A**: 편의 소형 · 오피스 · 건물 내 · 냉장 · D=12 · LT=2 · SL=95% · 자동
  2. **실측 체인**: LTD=24 · Z 1.65→2.38 · SS_stat 54.2 + buf 15.6 → raw ROP **93.8** → CAPA MaxCap **31.2** · 표시 SS **7.2** · Q **28** · 월·수·금
  3. **전문 토글** → **L1/L2/L3 출처 카드** · King Z · CAPA 항등 · (조정 시) D_eff 문구
  4. **B 실측 대조**: 주거 슈퍼·대로·상온 · ROP **37.04** · SS **21.04** · Q 28 · **월·목** · CAPA 캡 없음
  5. **(옵션) 경쟁 공세 시뮬**: 강도 슬라이더 → 유효 수요 −% · ROP/Q · **대응 방안 패널** (폴백/AI)
  6. 메시지: A는 **공간 병목**, B는 **맥락 SS 전부 반영**. 시뮬은 **상대 지수** (실측 점유율 아님)
- **Notes**: SSOT = `test_scenario_a/b_measured_walkthrough` · Kakao 없으면 행정동 경로

### Slide 13 - 로드맵 · 의사결정
- **Type**: Content
- **Key Message**: 근거 표와 정합은 올렸다. 다음은 **proxy를 실측·캐시로 교체**하는 일이다.
- **Details**:
  - **Now (DONE)**: Vercel · export · 일시·경쟁 프록시 · what-if · census · **`docs/evidence/`** · **D_eff 서사 정합**
  - **Next**: geo_override 재사용 · AI 타임박스 · places rate limit · 행사 캘린더 · 실측 KB · POS σ 운영 캘리브
  - **Not**: main 부활 · v1 검수 UI 복원 · 근거 없는 계수 과대 주장 · 시뮬 이중 쇼크
- **Visual**: Now / Next / Not 3열

### Slide 14 - Closing · Q&A
- **Type**: Closing
- **Message**:  
  v1으로 **결정론 제품** 습관을 만들었고,  
  피벗 뒤에는 **발주 레버(ROP·SS·Q·SL)** 로 옮겼습니다.  
  문헌 근거와 좁은 시연으로 “이 숫자의 근거”에 답하고,  
  상권·what-if까지 **엔진과 같은 식**으로 맞춰 두었습니다.
- **Contact**: GitHub `github.com/cidtw/md-preflight` · 브랜치 `pivot/project-direction` · https://baljumatch.vercel.app
- **Appendix pointers**: `docs/evidence/` · `docs/dev-journal-2026-07.md` · `docs/architecture.md` · `docs/redesign/pipeline.md` · `handoff/2026-07-20-p0-accuracy-ux.md`

---

## Style decision

| 항목 | 값 |
|------|-----|
| **확정** | `executive-minimal` (기존 유지) |
| **선정 이유** | 14장 스토리 아크를 슬라이드당 한 메시지로. 비즈니스+기술 혼성 |
| **Design note** | 표·공식은 카드 2–4개. 다이어그램은 단순 3단. Chart.js는 지표 슬라이드 1장. 신호 슬라이드는 다중 반경 |
| **미채택** | consulting-precision-grid · swiss |

**Stage 2 진입 조건**: 본 14장 문구·순서 승인 후 `slides-grab-design`으로 `slides/slide-01..14.html` **전량 재생성** (현 HTML은 아웃라인 동기화 패치 상태).

## Source map (사실 출처)

| 슬라이드 | 출처 |
|----------|------|
| 4 v1 성과 | `docs/dev-journal-2026-07.md` §0–3 · tag archive |
| 5 피벗·튜터 | redesign/ · 일지 국면 XI–XII · `docs/evidence/README.md` |
| 6–7 제품·아키텍처 | `docs/redesign/pipeline.md` · `docs/architecture.md` |
| 8 공식·근거 | `pipeline.md` · **`docs/evidence/evidence-matrix.md`** · King/ASCM |
| 9 Kakao·event·comp | `docs/setup-kakao-local.md` · `geo_enrichment.py` · `competition_saturation.py` |
| 10 패치 | 일지 국면 VIII–IX · **XII** · `handoff/2026-07-20-p0-accuracy-ux.md` |
| 11 지표 | 일지 · pytest **85** (2026-07-20) |
| 12 데모 | **`docs/evidence/demo-scope.md`** · simulate UI · 라이브 URL |
| 13 로드맵 | 일지 R17–R20 · P1 백로그 |

## Out of scope (이번 아웃라인 / Stage 1)

- `slide-*.html` 전량 자동 재생성·디자인 게이트·PDF (승인 후 Stage 2–3)
- 미검증 비즈니스 ROI 수치 창작
- v1 전 티켓 T1–T59 전수 나열
- main 브랜치 기능 재개

## Stage 2 체크리스트 (승인 후)

1. `slides-grab-design`: `style: executive-minimal` · 14장 HTML  
2. `slides-grab validate --slides-dir slides`  
3. Design gate (Pass A/B) · Critical 0  
4. 사용자 편집 승인 → `slides-grab pdf` (또는 PNG)
