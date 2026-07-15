# 매장 특화 ROP 재조정 — 최종 발표 장표

> **slides-grab Stage 1 (Plan only)**  
> 본 문서는 **내용·구성만** 고정한다. `slide-*.html` 생성·디자인 게이트·PDF export는 **아웃라인·스타일 승인 후** 진행한다.  
> 근거 일지: `docs/dev-journal-2026-07.md` · 아키텍처: `docs/architecture.md`

## Meta
- **Topic**: main 브랜치 v1(프로모션 사전검수) → 중간발표 피드백 → pivot ROP 제품까지의 개발 여정과 최종 산출
- **Target Audience**: 유통 비즈니스 이해관계자 · 테크 리드 · 멘토/평가 패널
- **Tone/Mood**: Restrained · Professional · Evidence-first (숫자·계약·데모 중심)
- **Slide Count**: 12 slides
- **Aspect Ratio**: 16:9
- **Presentation focus**: 피벗 이유 + 현재 동작하는 ROP 서비스 + 운영 레버
- **Style (확정)**: `executive-minimal`  
  - 여백·키노트형 · 메시지 밀도 낮게 · 비즈니스+기술 혼성 발표에 적합  
  - 미채택: `ppt-consulting-precision-grid` · `swiss-international-style`  
  - 이전 중간발표 참고: `ppt-samsung-ir-restrained` (구 7장)
- **Status**: **STAGE 2 GENERATED** — `executive-minimal` · 12 HTML in this deck · validate passed · design-gate pending/recorded

## Narrative Arc (한 줄)

```
문제(프로모션 오입력) → v1 라이브 검수 엔진 → 중간발표 피드백
  → 방향 피벗 → 매장 특화 발주 기준(ROP) → 운영 레버 정합 → 다음
```

## Slide Composition

### Slide 1 - Cover
- **Type**: Cover
- **Title**: 매장 특화 발주 기준 재조정
- **Subtitle**: MD Preflight — v1 사전검수에서 ROP 운영 레버 제품까지
- **Kicker**: 2026.07 · main → pivot/project-direction
- **Presenter**: 개발 권태원 (SaaS Platformer)
- **Notes**: 부제에 “Lead Time 고정 입력 · ROP·SS·요일·서비스 레벨 조정” 한 줄 가능

### Slide 2 - Agenda
- **Type**: Contents
- **Items**:
  1. 문제와 v1 해법 (main)
  2. 중간발표 성과와 한계
  3. 왜 피벗했는가
  4. 새 제품: 매장 특화 ROP
  5. 아키텍처 · 공식 · 운영 레버
  6. 검증 수치 · 데모 · 로드맵

### Slide 3 - 문제 정의 (유통 현장)
- **Type**: Content
- **Key Message**: 평균 표준 발주 기준으로는 매장마다 품절·과잉이 갈린다.
- **Details**:
  - **v1 문제(중간발표까지)**: 프로모션 등록 전 가격·기간·마진·재고 교차 오류 → 점포 혼선·마진 악화
  - **피벗 후 문제**: 업계·사내 평균 **Lead Time / ROP** 는 채널 평균에 가깝고, **입지·상권·CAPA·수요 피크**를 반영하지 못함
  - **제약**: 리드타임은 계약·품목 일정에 가깝다 → **“LT를 올려라”는 운영 레버가 아님**
- **Visual**: 좌 문제 카드 2장 (v1 / pivot) · 우 “조정 가능한 것 vs 고정 입력” 대비

### Slide 4 - v1 성과 스냅샷 (`main`)
- **Type**: Statistics
- **Key Message**: 7/1–7/13, 결정론 검수 엔진을 라이브 SaaS까지 올렸다.
- **Details**:
  - **10룰** 결정론 판정 · LLM은 **서술만** (계약 테스트로 경계 고정)
  - **SPA 워크스페이스**: 업로드 → 이슈 → CSV 수정 → 재검수
  - **프로덕션**: Vercel · Clerk · Neon · OpenAI/Anthropic fallback
  - **품질 KPI**: pytest **132 → 150** (T59 피크) · ruff / basedpyright clean
  - **아카이브**: 태그 `archive/v1-md-preflight` @ `b444be0`
- **Chart (optional)**: 막대 — pytest 궤적 47 → 104 → 132 → 150 (출처: 개발 일지 §2)
- **Notes**: 중간발표 7슬라이드 스토리 압축. 상세 티켓 T1–T59는 부록 정신으로 언급만.

### Slide 5 - 중간발표 피드백 → 피벗 동기
- **Type**: Content / Two-column
- **Key Message**: 피드백은 “더 많은 룰”이 아니라 **문제 정의 재정렬**을 요구했다.
- **Details**:
  - **유지한 자산**: 결정론 코어 · 근거 제시 · degrade 가능한 주변부
  - **내려놓은 것**: 고정 스키마 중심 프로모션 파일 검수 UI 복잡도
  - **새 목표**: 매장 파라미터 → **내부 점수 + KB** → **근거 있는 발주 기준 추천**
  - **브랜치 전략**: `main` 동결 · `pivot/project-direction` 에서 3단 파이프라인 재구축
- **Visual**: Before/After 화살표 (Preflight 검수 → ROP Adjust)

### Slide 6 - 제품 한 장 (What it does)
- **Type**: Content
- **Key Message**: 입력 3세션 → 0.5초 내부 연산 → 비교 대시보드 + 근거 리포트.
- **Details**:
  - **입력**: 매장 유형·규모·객단가 · 행정동·(선택) 상세주소 · 상권·접근성 · 품목·일소진 · **품목 LT** · 서비스 레벨 · 발주 요일 · (선택) 표준 ROP
  - **출력 레버**: ROP · 안전재고 · 1회 발주량 Q · 발주 요일/주기 · 서비스 레벨 Z  
  - **비레버**: Lead Time — **입력 유지, 추천 변동 없음**
  - **UX**: 위저드 → 로딩 → 리포트 (analyze는 내부 전용)
- **Visual**: 3단 플로우 다이어그램 Input → Analyze → Output

### Slide 7 - 아키텍처 (3단 파이프라인)
- **Type**: Content / Diagram
- **Key Message**: 스테이지를 늘어 확장하고, 판정은 결정론으로 유지한다.
- **Details**:
  - **input/** 템플릿·검증·유형↔규모/객단가 불일치 guidance
  - **analyze/** scoring · Kakao Local geo · KB · engine
  - **output/** 한 줄 recommendation · 비교표 · 근거 4블록(물류버퍼 / 수요·레버 / geo / CAPA)
  - **API**: `GET /api/template` · `POST /api/evaluate` · `GET /api/health`
- **Visual**: tldraw 권장 — 모듈 박스 + 데이터 화살표 (Stage 2에서 생성)
- **Notes**: v1의 “stateless path vs isolated auth/history” 교훈 → 새 제품은 주변부 최소, 코어 결정론 유지

### Slide 8 - 핵심 공식 (운영 레버 중심)
- **Type**: Content
- **Key Message**: LT는 곱하는 상수, 조정은 재고·발주 정책으로 한다.
- **Details**:
  - `LT = 품목 표준/계약 입력` (출력 delta = 0)
  - `Z = 서비스레벨 Z(90/95/99) + 맥락(변동성·품목·유동지수)`
  - `물류 버퍼 = D × max(0, 접근성 + KB 리스크일)`
  - `SS = Z·√(LT×변동성)·회전가중 + 버퍼`
  - `ROP = D×LT + SS` · CAPA 협소 시 MaxCap + 다회 소량
  - `Q · 요일 = 패턴 선택 또는 CAPA 자동 (예: 화·목 / 월·수·금)`
- **Visual**: 공식 카드 4장 (LT · Z · SS · ROP) + 작은 “요일 패턴” 칩
- **Do not invent numbers**: 데모 시 실제 evaluate 응답 수치 사용

### Slide 9 - 지도 유동지수 (Kakao Local)
- **Type**: Content
- **Key Message**: 정확한 주소가 있으면 주변 POI로 수요 맥락을 보수적으로 보정한다.
- **Details**:
  - 주소 검색 → 카테고리/버스 키워드 POI → `foot_traffic_index`
  - **탈포화**: 카테고리별 최근접 N · 순위 감쇠 · soft half-sat (도심에서 1.0 고착 방지)
  - 편의점(CS2)은 저가중 `convenience` · 지하철은 고가중
  - 키 없음/실패 → **행정동 경로 fallback** (evaluate 200 유지)
- **Visual**: 반경 원 + POI 칩 · index 스케일 예시 (지하철 1곳 ~0.25 / 도심 혼합 ~0.5)

### Slide 10 - 검증 · 품질 · 지표 궤적
- **Type**: Statistics / Timeline
- **Key Message**: 제품이 바뀌어도 “측정 가능한 품질” 습관은 유지했다.
- **Details**:
  - **v1 peak**: pytest **150** · 10룰 · 라이브 스택
  - **pivot skeleton**: **12** (의도적 슬림)
  - **ROP + ops 현재**: **30** · ruff / basedpyright 0
  - 계약: 결정론 파이프라인 · 예시 문장 하드코딩 금지 · LT 미조정 테스트
- **Chart**: 라인/막대 — pytest 시점별 (일지 §2 표 그대로)

### Slide 11 - 데모 스토리보드
- **Type**: Timeline / Steps
- **Key Message**: 3분 안에 “입력 → 레버 변화 → 근거”를 보여 준다.
- **Details**:
  1. 편의점 소형 · 오피스 · 건물 내 · 냉장 간편식 · LT=2 · SL=95% · 요일=자동
  2. 결과: ROP·SS·화목/월수금 · “LT 입력 유지” 행 확인
  3. SL 99%로 재실행 → Z·SS·ROP 상승 (여유 CAPA 매장으로 대비 시연)
  4. (선택) 정확한 위치 체크 + Kakao 키 → 유동지수·근거 블록
- **Notes**: 실패 시 fallback 메시지도 의도된 UX로 설명

### Slide 12 - Closing · 로드맵 · Q&A
- **Type**: Closing
- **Message**:  
  v1으로 **신뢰 가능한 결정론 제품** 습관을 만들었고,  
  피벗 후 **매장이 실제로 움직이는 발주 레버**에 그 습관을 옮겼습니다.
- **Next**:
  - R8 배포·Kakao 시크릿 패리티
  - R9–R10 실측 KB · Agent 교체 포트
  - R11–R12 품목 마스터 · 요일 캘린더 UX
- **Contact**: GitHub `github.com/cidtw/md-preflight` · 브랜치 `pivot/project-direction`
- **Appendix pointers**: 개발 일지 · architecture.md · redesign board

---

## Style decision

| 항목 | 값 |
|------|-----|
| **확정** | `executive-minimal` |
| **선정 이유** | 여백·풀블리드에 가까운 키노트 톤 · 12장 스토리 아크를 슬라이드당 한 메시지로 읽히게 |
| **Design note** | 표·공식은 카드 2–4개로 압축 · 다이어그램은 단순 3단 플로우 · Chart.js는 지표 슬라이드 1장만 |
| **미채택** | consulting-precision-grid (밀도↑) · swiss (격자 강조) |

**Stage 2**: 아웃라인 12장 문구에 이의 없을 때 `slides-grab-design` 진행 (현재는 내용 고정만).

## Source map (사실 출처)

| 슬라이드 | 출처 |
|----------|------|
| 4 v1 성과 | `docs/dev-journal-2026-07.md` §0–3 · tag archive |
| 5 피벗 | `2026-07-14-Project-Redesign.md` · redesign/ |
| 6–8 제품·공식 | `docs/redesign/pipeline.md` · `docs/architecture.md` |
| 9 Kakao | `docs/setup-kakao-local.md` · `geo_enrichment.py` |
| 10 지표 | 일지 §2 · 현재 pytest 30 |
| 11 데모 | `POST /api/evaluate` 실응답 |

## Out of scope (이번 아웃라인)

- 실제 HTML/PDF 생성
- 미검증 비즈니스 ROI 수치 창작
- v1 전 티켓 T1–T59 전수 나열 (발표 본문에서는 성과 스냅샷만)
