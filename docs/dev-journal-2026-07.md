# MD Preflight 개발 일지 — 2026년 7월 전체 흐름

> **용도**: 최종 발표 때 “무엇을 언제, 왜 만들었는지”를 **7/1 착수 → 7/13 중간발표 → 7/14 피드백 → 방향성 재설계**까지 한 흐름으로 설명하기 위한 정본.  
> **범위**: 2026-07-01 ~ (진행 중, 국면 VI 재설계 포함)  
> **근거**: git 커밋, `handoff/` 노트, 티켓 T1~T59, 재설계 지시 `2026-07-14-Project-Redesign.md`, 당일 검증 수치  
> **관련**: `docs/redesign/`, `archive/v1-md-preflight/`, v1 설계 원문 = tag `archive/v1-md-preflight`

---

## 0. 한 장 요약 — 전체 스토리 아크

```
[7/1–2]  뼈대          초기 커밋 · 룰 확장 · fallback 서술 · 샘플
    ↓
[7/4]    판정 계약      10룰 · 조인 불변식 · LLM 경계(T5–9) · README · demo
    ↓
[7/5–6]  제품 UI        DESIGN · SPA · CSV 편집 · 체크리스트 · 이력 스텁
    ↓
[7/7–8]  실배선·배포     OpenAI/Neon/Clerk · T40/T41 격리 · Vercel 라이브
    ↓
[7/9–10] 완성도         hardening · 덱 · 시드 · 데모 신뢰성 (발표 7/13로 연기)
    ↓
[7/11–13] 발표·모듈화    리허설 창 · app.js PR1–3 분리 (7/13 커밋)
    ↓
[7/14 a.m.] 피드백 대응  별칭 · 4화면 · 매핑 감사 · 설정 · 어댑터 (T48–T59)
    ↓
[7/14 p.m.] 방향 피벗    v1 아카이브 · 3단 파이프라인 스켈레톤 · 재설계 판 (국면 VI)
    ↓
[7/14 eve] ROP 제품화   매장 파라미터 → 추천·근거 리포트 (국면 VII)
    ↓
[7/14 late] 운영 레버   지도 POI · LT 입력 유지 · SS/Q/요일/SL (국면 VII+)
    ↓
[7/15]     정확도 수정  SS∝수요 · 비교표·geo 귀속 · size 기본값 (국면 VIII)
    ↓
[7/16]     안정화·기능  CAPA/Q · 추천 윤문 · export · 일시 유동 옵션 (국면 IX)
    ↓
[7/16+]    제3자 시연   프리셋·demo.sh·폴리시 (국면 X)
    ↓
[7/19]     근거 심화   튜터 피드백 · 문헌 매트릭스 · 스코프 축소 (국면 XI)
    ↓
[7/19–20]  상권·시뮬   경쟁 포화 · what-if · census · P0 정합 (국면 XII)
    ↓
[7/21]     발표 UI 윤문  카드 평이화 · 기술스택 상단 · 스크롤 · 교육 크레딧 (국면 XIII)
```

| 국면 | 기간 | 한 줄 목표 | 대표 산출 |
|------|------|------------|-----------|
| **I. 엔진 코어** | 7/1–4 | 결정론 검수가 돌아가게 | 10룰, ingest, API, D3 계약 |
| **II. MD 워크스페이스** | 7/5–6 | 브라우저에서 쓰고 고치게 | SPA, 편집, 체크리스트, 테마 |
| **III. 라이브 제품** | 7/7–9 | 프로덕션에서 안 죽게 | Clerk/Neon/LLM, degrade, harden |
| **IV. 발표 품질** | 7/9–13 | 스토리·데모가 안 깨지게 | 덱, seed, 스모크, 모듈 분리 |
| **V. 중간발표 이후** | 7/14 오전 | 약점(고정 컬럼·한 화면) 해소 | T48–T59, UI 리프레시 |
| **VI. 방향성 재설계** | 7/14 오후 | v1 동결, 모듈 3단 판 | archive, pipeline skeleton |
| **VII. ROP 서비스** | 7/14 저녁 | 매장 특화 발주 기준 재조정 MVP | scoring, KB, report UI |
| **VII+ 운영 레버** | 7/14 심야~ | 현실적 조정 대상 정합 | Kakao POI, LT 고정 출력, SL·요일 |
| **VIII. 정확도 패치** | 7/15 | 리뷰 P0 정확도·UX 회귀 수정 | SS∝D, Z/geo 표시, size 기본값 |
| **IX. 안정화·일시 유동** | 7/16 | CAPA/UX 픽스, 추천 윤문, 행사 수요 증분 | Q clamp, export 위임, event 200m |
| **X. 제3자 시연** | 7/16+ | 데모 프리셋, 스모크, 탭 폴리시 | demo_scenarios, demo.sh, favicon |
| **XI. 근거 심화** | 7/19 | 객관 출처 매핑, 논리 완결, 스코프 축소 | `docs/evidence/`, 일지·발표 반영 |
| **XII. 상권·시뮬·정합** | 7/19–20 | 경쟁·what-if·census, 식·UI 일치 | D_eff 서사, 시뮬 패널, 91점 스냅샷 |

**불변 원칙**

| 구간 | 원칙 |
|------|------|
| **국면 I–V (v1, D3 / `main`)** | 판정 = 결정론 룰. 서술 = LLM(실패 시 fallback). 검수 비로그인 200. 이력은 격리·append-only |
| **국면 VI+ (재설계 / `pivot/project-direction`)** | 판정 = 결정론 **가중치 점수**. 입력 = 파라미터 템플릿. 출력 = **한 줄 recommendation**. **LT는 품목 입력(유지)**. 조정 레버 = ROP·SS·Q·발주 요일·서비스 레벨. **SS 통계항∝일평균 소진** (VIII). 미입력 기본값 = 규모 밴드. **D_eff = D × event × competition** (IX/XII). **근거 3층(L1–L3)** (XI). **서사·시뮬 충격은 엔진과 일치** (XII). **main은 아카이브(변경 금지)** |

**v1 복원 키**: 태그 `archive/v1-md-preflight` @ `b444be0` · 문서 `archive/v1-md-preflight/`

---

## 1. 티켓 전체 맵 (T1 → T53)

### 1.1 엔진·계약 (Phase I)

| ID | 제목 | 대략 시점 | 상태 |
|----|------|-----------|------|
| T1 | 커밋·서브모듈 보존 | 7/4 | DONE |
| T2 | `POST /api/preflight` | 7/4 | DONE |
| T3 | `report.md` 다운로드 | 7/4 | DONE |
| T4 | 문서 동기화 | 7/4 | DONE |
| T5 | LLM 서술 인터페이스 | 7/4 | DONE |
| T6 | Anthropic 생성기 | 7/4 | DONE |
| T7 | `use_llm` 배선 | 7/4 | DONE |
| T8 | LLM 결정론 계약 테스트 | 7/4 | DONE |
| T9 | 업로드 에러 규약 400/413 | 7/4 | DONE |
| T10 | ingest 조인 1:1 불변식 | 7/4 | DONE |
| T11 | `INCOMPLETE_PRODUCT_MASTER` | 7/4 | DONE |
| T12 | 문서 10룰 재동기화 | 7/4 | DONE |

### 1.2 프론트·워크플로 (Phase II)

| ID | 제목 | 대략 시점 | 상태 |
|----|------|-----------|------|
| T13–T16 | 메인 카피·푸터·리포트 파일명·요약 상단 | 7/6 | DONE |
| T17 | 클라이언트 CSV 모델·인페이지 편집 | 7/6 | DONE |
| T18 | 외부 소스 커넥터 스텁 | 7/6 | DONE |
| T19 | 파일별 AI 요약 v2 | 7/6 | DONE |
| T20 | 인터랙티브 체크리스트 적용 | 7/6 | DONE |
| T21–T24 | 소스 아이콘·한글 에러·파일별 이슈·CSV 버그픽스 | 7/6 | DONE |
| T25 | 교차 파일 `related_locations` | 7/6 | DONE |
| T26–T29 | 체크리스트 인라인·재검수 배지·행/열 추가 | 7/6 | DONE |
| T30–T32 | 이력 영속 스텁·Clerk 게이트 스텁·대시보드 골격 | 7/6 | DONE |

### 1.3 실배선·프로덕션 (Phase III)

| ID | 제목 | 대략 시점 | 상태 |
|----|------|-----------|------|
| T33–T35 | 네비/테마·CSV 삭제·이력 런 로그 | 7/7 | DONE |
| T36 | 실 LLM 스모크 | 7/7 | DONE |
| T37–T39 | Postgres 이력 · Clerk 실배선 · OpenAI 어댑터 | 7/7 | DONE |
| T40 | 이력 스토어 생성 격리 (F1) | 7/7–8 | DONE |
| T41 | Clerk aud→azp/iss 검증 (F2) | 7/7–8 | DONE |
| T42–T43 | Settings API 키 · HTML config 플레이스홀더 | 7/9 | DONE |

### 1.4 중간발표 이후 (Phase V)

| ID | 제목 | 시점 | 상태 |
|----|------|------|------|
| T48 | 컬럼 별칭 수렴 | 7/14 | **DONE** |
| T49 | 해시 라우팅 + 설정 뷰 | 7/14 | **DONE** |
| T50 | `column_mappings` 노출 | 7/14 | **DONE** |
| T51 | alias_ko 샘플 + 업로드 힌트 | 7/14 | **DONE** |
| T52 | 누락 컬럼 제안 UX | 7/14 | **DONE** |
| T53 | 설정 카탈로그(임계값·룰·별칭) | 7/14 | **DONE** |
| T54 | (선택) stub 멤버 프로필 | 7/21–22 | 예정 |
| T55 | 회귀·문서 · freeze | 7/23–24 | 예정 |
| T56 | 입력 어댑터 ADR (X/Z) | 7/14 | **DONE** |
| T57 | N파일 업로드 + 역할 매핑 UI | 7/14 | **DONE** |
| T58 | 단일 xlsx 멀티시트 → 프레임 분리 | 7/14 | **DONE** |
| T59 | 역할 매핑 Report/MD 기록 | 7/14 | **DONE** (v1 종료) |

### 1.5 재설계 준비 (Phase VI) — v1 티켓 번호 체계와 분리

| ID | 제목 | 시점 | 상태 |
|----|------|------|------|
| P1 | v1 아카이브 태그·문서 (`archive/v1-md-preflight`) | 7/14 | **DONE** |
| P2 | 백엔드 keep/discard 리뷰 | 7/14 | **DONE** |
| P3 | 3단 파이프라인 스켈레톤 + API (`/api/template`, `/api/evaluate`) | 7/14 | **DONE** |
| P4 | 재설계 판 `docs/redesign/` | 7/14 | **DONE** |
| P5 | README·AGENTS·BRIEF·일지·의존성 슬림화 | 7/14 | **DONE** |
| R0–R6 | ROP 도메인·테이블·엔진·UI·근거 패널 | 7/14 | **DONE** |
| R7a | 멀티 세션 입력 위저드 | 7/14 | **DONE** |
| R7b | 정확한 위치 · 지도 POI 유동지수 (Kakao Local) | 7/14 | **DONE** |
| R7c | foot_traffic 포화 완화 (카테고리 캡·소프트 반포화) | 7/14 | **DONE** |
| R7d | LT 출력 고정 · 운영 레버(SS/Q/주기) | 7/14 | **DONE** |
| R7e | 서비스 레벨 · 발주 요일 패턴 입력 | 7/14 | **DONE** |
| R15–R16 | 근거 패키지 · 실측 σ/지연 경로 | 7/19 | **DONE** |
| R17 | 경쟁 포화 수요 분산 (주소 전용) | 7/19–20 | **DONE** |
| R18 | what-if 경쟁 시뮬 + 매출하락 조언 UI | 7/19–20 | **DONE** |
| R19 | 데모 census 스냅샷 · Vercel 임베드 | 7/19–20 | **DONE** |
| R20 | P0 서사·이중적용·분류기 정합 | 7/20 | **DONE** |
| R8+ | 실측 KB · 행사 캘린더 · geo 캐시 | 이후 | **TODO** |

### 1.6 브랜치 타임라인 (main ↔ pivot)

| 브랜치 | 시점 | 역할 |
|--------|------|------|
| **`main`** | ~`b444be0` | v1 MD Preflight 정본. 프로모션 사전검수 · T1–T59 · pytest **150** 피크 · Vercel 라이브 |
| 태그 `archive/v1-md-preflight` | 7/14 | main 스냅샷 동결 (복원 키) |
| **`pivot/project-direction`** | 7/14~ | v1 패키지 제거 후 ROP 파이프라인. 본 일지 국면 VI–VII+ 정본 브랜치 |

> 발표 시: “**main은 중간발표까지 완성된 v1**, **pivot은 피드백 뒤 방향을 바꾼 제품**”으로 한 줄에 구분한다.

---

## 2. 지표 궤적 (대략)

| 시점 | pytest (참고) | 제품 상태 |
|------|---------------|-----------|
| 7/2 전후 | 초기 스위트 | 룰 확장·서비스 분리 |
| 7/4 상태 스냅샷 | **47** | T1–T12 핵심 엔진 거의 완료 |
| 7/9 T42/T43 | **104** | 프로덕션 hardening 직전·직후 |
| 7/9–10 덱/폴리시 | **132** | 중간발표 KPI로 고정 |
| 7/14 T48–T51 | **141–142** | 별칭·라우트·UI |
| 7/14 T52–T53 | **143** | catalog + error UX |
| 7/14 T56–T59 (`main` 피크) | **150** | v1 입력 어댑터 · 아카이브 기준점 |
| **7/14 재설계 스켈레톤** | **12** | 파이프라인 unit/API only (의도적 슬림) |
| **7/14 ROP MVP** | **14** | 스코어링 · KB · 리포트 UI |
| **7/14 ROP + geo/ops** | **30** | Kakao · 탈포화 · LT 고정 · SL·요일 |
| **7/15 정확도 패치** | **32** | SS∝수요 · 비교표 수정 · CAPA/geo 테스트 보강 |
| **7/16 안정화·event** | **46–47** | CAPA/Q · export · 일시 유동 · 시연 프리셋 |
| **7/19 근거·R16** | **~60대** (확장) | evidence · measured σ · 시나리오 A 워크스루 |
| **7/20 상권·시뮬·P0** | **85** | competition · sim · census · D_eff 서사 · 분류기 |
| 이후 | green + R8+ | geo 캐시 · 실측 KB · 행사 캘린더 |

---

## 3. Part A — 7/1 ~ 7/13 빌드 과정

### 2026-07-01 ~ 07-02 (화–수) — 프로젝트 착수 · 룰 확장

| 필드 | 내용 |
|------|------|
| **테마** | “프로모션 사전검수” 코드베이스를 기동 |
| **핵심 커밋** | `5050e23` Initial commit · 마진/재고 룰 추가 계열 |
| **산출** | FastAPI 골격 · 초기 룰 세트 · fallback 서술·리포트 서비스 분리 시작 |
| **핸드오프** | `2026-07-02-mvp-rule-expansion.md` · `2026-07-02-workspace-smoke-test.md` |

**한 줄**  
> 유통 등록 전 검수 문제를 **결정론 룰 엔진**으로 풀겠다는 방향을 코드에 박기 시작했다.

**수행 (요약)**
- [x] 저장소 초기화 및 앱 패키지 구조
- [x] 마진·재고·입고·증정 등 룰 확장 (당시 8룰 체계 → 이후 10룰로 정합)
- [x] `llm_service` fallback · `report_service` Markdown
- [x] `docs/rule-matrix.md` · 샘플·스모크

---

### 2026-07-03 (목) — (기록 소량 · 준비일)

| 필드 | 내용 |
|------|------|
| **테마** | 본격 T1–T12 스프린트 직전 정리 (상세 커밋은 7/4 클러스터) |
| **상태** | 7/4 대량 커밋으로 흡수된 작업일 가능 |

---

### 2026-07-04 (금) — 엔진 계약의 날 (Phase I 피크)

| 필드 | 내용 |
|------|------|
| **테마** | API 풀파이프라인 · 10룰 · LLM 경계 · 업로드 규약 · 포트폴리오 README |
| **핵심 커밋** | `a2ad668` 조인 불변식 · `ce1874f` LLM 경계 · `7c03230` full pipeline · `1f3b3d4` README · `ffe161b` demo/dirty |
| **검증 스냅샷** | 상태 노트 기준 **pytest 47** (이후 스위트 확장) |
| **핸드오프** | `t1`~`t12` · `t5-t6` · `t7-t8-t9` · `status-and-forward-plan` · architecture review |

**의사결정**
- 판정 경로에 LLM 입력 금지 → **T5 인터페이스 + T8 계약 테스트**로 증명 가능해야 함
- 룰 수 8→**10** (`INCOMPLETE` · `DUPLICATE` 등 데이터 정합성)
- 확장자 **400** · 용량 **413** · 컬럼 **422** (T9)

**수행 (요약)**
- [x] T2/T3 엔드포인트 · T10/T11 정합성 룰
- [x] T5–T7 NarrativeGenerator · use_llm · fallback-on-error
- [x] T8 적대적 목 (issues 변조·프롬프트 인젝션·과잉 checklist)
- [x] T9 업로드 검증 공용
- [x] README “왜 LLM에 판정 안 맡겼나” · `demo.sh` · dirty 10룰 픽스처

**한 줄**  
> **“같은 입력이면 같은 이슈”**와 **“LLM은 서술만”**이 코드, 테스트, 문서에 한꺼번에 잠긴 날.

---

### 2026-07-05 (토) — 발표 초안 · 제품 카피

| 필드 | 내용 |
|------|------|
| **테마** | 개발 초안 발표 덱·카피 폴리시 (제품 스토리 정리) |
| **핸드오프** | `2026-07-05-dev-draft-presentation-*` |
| **의미** | 기술 구현과 별도로, **청중이 들을 말**로 문제와 해법을 고정 |

---

### 2026-07-06 (일) — MVP 프론트엔드 폭발적 확장 (Phase II)

| 필드 | 내용 |
|------|------|
| **테마** | 브라우저에서 업로드 → 검수 → 수정 → 재검수 루프를 완성 |
| **브랜치** | `feat/mvp-frontend` 연속 PR (#2–#7) |
| **핵심 커밋** | `8bc78de` MVP FE+DESIGN+Vercel · `d7bd2fc` CSV 편집 · `e7cd7fe` T21–27 · `cf108fb` T28–32 |
| **핸드오프** | T13–T32 개별 노트 · `2026-07-06-summary` · architecture-decisions v1–v4 · feedback v1–v4 |

**아키텍처 결정 (v1→v4 요약)**
- 무상태 판정 경로 vs 이력/인증 경로 **격리**
- 선택 로그인 · 이력 append-only · PII/원본 미저장
- 프론트는 **빌드 없는 static SPA** (FastAPI 동일 오리진)

**수행 묶음**
| 묶음 | 티켓 | 내용 |
|------|------|------|
| 카피·내비 | T13–T16 | 직관 카피 · AI 토글 예시 · 푸터 · 요약 상단 · 리포트 파일명 |
| 편집 루프 | T17·T20·T24·T26–T29 | CSV 편집·체크리스트 적용·버그픽스·행열 추가 |
| 서술·소스 | T18–T19·T21 | 커넥터 스텁 · 파일별 요약 · 소스 아이콘 |
| 이슈 UX | T22–T23·T25 | 한글 표시 · 파일별 그룹 · related_locations |
| 이력 골격 | T30–T32 | 영속 인터페이스 스텁 · Clerk 게이트 스텁 · 대시보드 스켈레톤 |

**한 줄**  
> 백엔드 엔진 위에 **MD가 실제로 만지는 워크스페이스**가 하루 만에 붙었다.

---

### 2026-07-07 (월) — 실배선 + 프로덕션 병합 (Phase III 피크 · 중간발표 축)

| 필드 | 내용 |
|------|------|
| **테마** | OpenAI·Postgres·Clerk 실배선 · T40/T41 정합성 · main 머지 · Vercel 라이브 |
| **핵심 커밋** | `14d0e1b` T33–T39 · `8eaaa30` T40–T41 · `8ae4071` merge feat/mvp-frontend |
| **핸드오프** | `t33-t35-t39` · `t36` · `t37-t38` · `t40-t41` · `production-deploy` · midterm slidev |

**수행**
- [x] T33 네비·플로팅 테마 · T34 CSV 삭제/되돌리기 · T35 이력 런 로그
- [x] T36 실 LLM 스모크 · T37 Neon 이력 · T38 Clerk · T39 OpenAI 어댑터
- [x] T40: history store 생성 실패 → 인메모리 degrade, **검수 200 유지 (F1)**
- [x] T41: Clerk 세션 `aud` 대신 `azp`/`iss` (F2)
- [x] Vercel env · production URL 200

**한 줄**  
> “데모 가능한 로컬 앱”에서 **라이브 SaaS 스택**으로 올렸다. 중간발표 기술 데모의 바닥이 깔렸다.

---

### 2026-07-08 (화) — 네트워크·실환경 점검

| 필드 | 내용 |
|------|------|
| **테마** | 프로덕션 경로 관측 · E132 네트워크 체크 등 운영 이슈 핸드오프 |
| **핸드오프** | `2026-07-08-E132-Network-Check-Handoff.md` |
| **의미** | 배포 직후 생긴 **실환경 마찰**을 티켓·노트로 남겼다 |

---

### 2026-07-09 (수) — Hardening · 덱 · 발표일 재편

| 필드 | 내용 |
|------|------|
| **테마** | T42/T43 · production-harden · 7슬라이드 덱 · **발표 7/10→7/13 연기** 반영 |
| **핵심 커밋** | `a7549d1` keys/seed · `96a29d2` harden · `ef20868` final deck · CSV/Clerk UI 픽스 |
| **검증** | T42/T43 시점 **104** → 덱 KPI **132** 로 정리 |
| **핸드오프** | `2026-07-09-summary` · `production-hardening` · `replan-through-0713` |

**의사결정**
- 버퍼 기간에 **신규 기능 스코프 금지** → 데모 신뢰성·발표 품질
- 7/12 soft freeze 권고 (이후 replan 문서)

**수행**
- [x] F3/F4 (API 키 Settings 일원화 · config placeholder)
- [x] run access · LLM fallback · 인증 harden
- [x] 발표 덱 v1 · outline · seed 스크립트 방향

**한 줄**  
> 기능을 더 넣기보다 **안 깨지는 라이브**와 **한 번에 읽히는 덱**에 힘을 썼다.

---

### 2026-07-10 (목) — 데모 신뢰성 데이

| 필드 | 내용 |
|------|------|
| **테마** | 프로덕션 health · seed · LLM 스모크 · 덱 날짜 7/13 |
| **핸드오프** | `2026-07-10-summary` · `day07-demo-reliability` |
| **완료** | health clerk/postgres · 비로그인 검수 · 이력 401 · Neon seed · 모델 ID 확증 |
| **잔여** | Clerk **실브라우저** e2e (사용자 액션) · 발표 계정 seed 정합 |

**한 줄**  
> 발표 전 “라이브 경로가 죽지 않는다”를 API 레벨에서 다시 못 박았다.

---

### 2026-07-11 ~ 07-12 (금–토) — 리허설·프리즈 창 (계획상)

| 필드 | 내용 |
|------|------|
| **테마** | 발표 멘트·데모 시나리오 · 풀 검증 · 코드 프리즈 (replan 권고) |
| **코드 커밋** | 이 구간에 큰 기능 커밋 없음 (의도적 안정화) |
| **계획 정본** | `handoff/2026-07-09-replan-through-0713.md` § 7/11–12 |

---

### 2026-07-13 (일) — 중간발표 D-day · FE 모듈 분리

| 필드 | 내용 |
|------|------|
| **테마** | 중간발표 · 발표 직후/병행 유지보수 |
| **핵심 커밋** | `ca91cde` refactor(web): split app.js into PR1–3 UI modules |
| **의미** | 덩치 큰 단일 `app.js`를 모듈로 나눔. **7/14 이후 UX 개편의 발판**이 됐다 |

**중간발표에서 드러난 것 (→ Part B 입력)**
1. 고정 csv/xlsx, 고정 컬럼에 대한 질문  
2. 교육 시간·타겟 유저  
3. **column key 변경 미테스트**  
4. 자가진단: 실무 edge, SPA 한 덩어리, Clerk 테스트 마찰  

**한 줄**  
> 제품은 라이브·검증 완료 상태로 발표했다. 피드백은 **다음 스프린트 백로그의 입구**가 됐다.

---

## 4. Part B — 7/14 ~ 7/23 (중간발표 이후)

> 상세 세션 노트는 아래 유지. 계획 정본: `handoff/2026-07-14-plan-through-0724.md`.

### 0′. 피드백 → 과제 매핑

| # | 피드백 / 자가진단 | 기간 내 대응 | 기간 외 |
|---|-------------------|--------------|---------|
| Q1 | 고정 스프레드시트만? | T51 샘플·힌트 | 다중 포맷 |
| Q2 | 교육 1시간? | T49·T53 설정 카탈로그 | 풀 온보딩 |
| Q3 | column key 변경? | **T48–T52** | 고객별 매핑 UI |
| S1 | 실무 edge | “ERP 달라도 같은 10룰” | 채널 retrieve |
| S2 | 한 화면 SPA | **T49** 4화면 | 자체 멤버 DB |

### 티켓 보드 (7/14+)

| ID | 상태 |
|----|------|
| T48–T53 | **DONE** (7/14) |
| T54 | 예정 (선택) |
| T55 | 예정 (freeze) |

### 지표

| 일자 | pytest | 비고 |
|------|--------|------|
| 7/14 시작 직전 | 132 | 발표 KPI |
| **7/14 종료** | **143+** | T48–T59 (별칭·어댑터·시트·역할 감사) |

---

### 2026-07-14 (월) — 방향 고정 + T48–T53 일괄 착수·완료

| 필드 | 내용 |
|------|------|
| **테마** | 중간발표에서 나온 약점 두 축(고정 컬럼, 한 화면)을 **고칠 수 있는 빌드**로 메움 |
| **커밋** | `b3bce30` T48–T51+UI · `b04b5b9` T52–T53 · `8660119` architecture-easy |
| **배포** | main push → Vercel |

#### 의사결정
| ID | 내용 |
|----|------|
| D-A | 7/24 = 중간 릴리스 (final RC 전 범위 백로그) |
| D-B | 별칭 레이어 최우선 (룰 10개 불변) |
| D-C | 해시 4화면 (MPA 전환 아님) |
| D-D | 별칭 = 명시 테이블 (fuzzy ML 금지) |
| D-E | 설정 = 읽기 전용 카탈로그 먼저 |

#### 수행 체크리스트
- [x] **T48** `column_aliases` → `prepare_source_frame`
- [x] **T49** `#/` `#/run` `#/dashboard` `#/settings`
- [x] **T50** `column_mappings` API·MD·결과 UI
- [x] **T51** `data/samples/alias_ko` · `/samples` · 업로드 힌트
- [x] **FE 리프레시** 히어로·패널·드롭존
- [x] **T52** 누락 컬럼 한글 토스트 + 별칭 예 힌트
- [x] **T53** `GET /catalog` · 임계값·룰·별칭 설정 화면
- [x] 개발 일지·아키텍처 easy 문서

#### 검증
```
ruff · basedpyright · pytest 143 · verify_router/error_format/dom_util
```

#### 한 줄 회고
> 중간발표가 남긴 구멍은 final RC 전체가 아니라 **ingest 유연성, 화면 구조, 설정 SSOT**로 막았다. 판정 경계(D3)는 그대로 둔다.

#### 1.12 연속 세션 — T56–T59 (입력 어댑터 X/Z)

| 항목 | 내용 |
|------|------|
| **결정** | X/Z 채택: 정규 3프레임 유지, 어댑터로 입력 개방 (Y 폐기) |
| **T56** | ADR `docs/adr/0001-input-adapter-canonical-frames.md` · Frame/Role/Mapping 용어 |
| **T57** | N파일 업로드 · `POST /detect-roles` · 역할 매핑 UI |
| **T58** | 멀티시트 xlsx 시트 단위 아티팩트 분리 · `promotion_sheet` 등 선택자 · `multisheet` 샘플 |
| **T59** | `role_mappings` 폼 → Report/MD/결과 UI 감사 기록 |
| **커밋** | `8c38c20` (T56–57) · `ded69df` (T58–59) · pytest **150** |

---

### 2026-07-14 (월) 오후 — 방향성 재설계 준비 (국면 VI) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | 프로젝트 방향 자체를 바꿈. v1 아카이브 + 모듈 3단 파이프라인 판 제작 |
| **지시문** | `2026-07-14-Project-Redesign.md` |
| **브랜치** | `pivot/project-direction` (remote tracking) |
| **아카이브 태그** | `archive/v1-md-preflight` → commit `b444be0` |
| **검증** | `ruff` pass · `basedpyright app` 0 errors · **pytest 12 passed** |

#### 피드백/문제 인식 (지시 §1)

1. **기능 과다**: 10룰, 어댑터, Clerk/Neon, 대형 SPA가 한 제품에 공존  
2. **서비스 근거 빈약**: 조사 기반 평가 가중치·추천 논리가 제품 중심에 없음  
3. **가벼운 서비스 + 무거운 웹**: 본체에 비해 웹 표준·프로덕션 표면이 체감 부하를 키움  

#### 방향 재설정 (지시 §2)

1. 스코프를 좁히고 논리·근거를 분명히  
2. 파라미터 입력 → 사전 조사 가중치 분석 → **한 줄 recommendation**  
3. 프레임워크를 분명히, 구조는 간결히, 환경과 무관하게 같은 경험  
4. 블록·모듈형으로 이후 기능을 붙일 수 있게  

> **서비스 세부 구성(도메인, 실 가중치, 본 UI)은 준비 과정이 끝난 뒤** board R0+에서 진행.

#### 수행 (지시 §3 준비 과정 — 전부)

| # | 작업 | 산출 |
|---|------|------|
| 1 | main/v1 자료 백업·아카이브 | 태그 `archive/v1-md-preflight` · `archive/v1-md-preflight/{README,MANIFEST,DISCARD-REVIEW}.md` |
| 2 | 파이프라인 3단 재편 + 버릴 것 폐기 + 모듈 백엔드 사전 작업 | 아래 *구조·폐기* 상세 |
| 3 | 재설계 판 제작 | `docs/redesign/{README,direction,pipeline,board}.md` |

##### 활성 파이프라인 구조 (input → analyze → output)

```
app/pipeline/
  input/template.py     # GET /api/template · 파라미터 검증
  analyze/weights.py    # 플레이스홀더 기준·가중치 (조사 전 DEFER)
  analyze/engine.py     # 결정론 점수 · band strong/moderate/weak
  output/recommendation.py  # 한 줄 recommendation
  runner.py             # 오케스트레이션 단일 진입
app/api/routes.py       # GET /api/health · /api/template · POST /api/evaluate
app/web/                # 최소 HTML/CSS/JS 셸 (대형 SPA 제거)
```

##### 활성 트리에서 제거 (DISCARD — 복원은 태그)

| 영역 | 제거된 대표 경로 |
|------|------------------|
| 판정 엔진 | `app/rules/*` (10룰) |
| 입력 정제 | `app/ingest/*`, `app/domain/*` |
| 서비스 층 | `app/services/*` (LLM, history, clerk, validation_engine, …) |
| 소스 스텁 | `app/sources/*` |
| v1 스키마 | `app/schemas/{report,issue,history,catalog,…}` |
| 대형 SPA | `app/web/*.mjs` 다수 · `app/web/samples/**` |
| 데모/검증 스크립트 | `demo.sh` · `scripts/verify_*.mjs` · `scripts/seed_db.py` |
| v1 테스트 스위트 | `tests/test_rules.py` 등 전체 → 파이프라인 12테스트로 교체 |

##### 의존성 슬림화

- **제거**: pandas, openpyxl, anthropic, openai, psycopg, PyJWT, python-multipart, numpy 등  
- **런타임 유지**: fastapi, pydantic, pydantic-settings, orjson, uvicorn  
- **dev**: ruff, basedpyright, pytest, httpx2  
- `pyproject.toml` version **0.2.0** · `uv.lock` 재생성  

##### 문서·계약 정합

| 파일 | 변경 |
|------|------|
| `README.md` | 재설계 스켈레톤 중심으로 전면 재작성 |
| `PROJECT_BRIEF.md` | 새 한 줄·파이프라인·비목표 |
| `AGENTS.md` | 활성 경로·검증 커맨드·v1 복원 주의 |
| `BACKEND_ARCHITECTURE.md` / `DESIGN.md` | 당시 ARCHIVED 배너 → **2026-07-20 활성 트리 삭제** (태그 보존) |
| `vercel.json` | `app/web/**` only (samples 경로 제거) |
| `.env.example` | 슬림 (Clerk/DB/LLM 키 필수 아님) |
| `docs/redesign/*` | 방향·파이프라인 계약·보드 |
| 본 일지 | §0 국면 VI · §1.5 · §2 지표 · 본 소절 |

##### 검증 기록 (당일 세션)

```
uv run ruff check app tests     # All checks passed
uv run basedpyright app         # 0 errors
uv run pytest                   # 12 passed
```

#### 한 줄 회고
> v1은 **태그로 완전히 동결**하고, 활성 트리는 “파라미터 → 가중치 → 한 줄 추천”만 남는 **빈 판**으로 리셋했다. 다음 일은 코드가 아니라 **근거(R0–R2)**다.

#### 의도적으로 하지 않은 것 (지시 준수)

- 실 서비스 도메인·조사 가중치 확정 (board R0+ **NOT STARTED**)  
- 본격 UI 폴리시·프레임워크 선정  
- v1 기능을 새 파이프라인에 억지 이식  

---



### 2026-07-14 (월) 저녁 — ROP 서비스 플로우 빌드 **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | `2026-07-14-New-Service-Flow.md` 기준 매장 특화 발주 기준 재조정 MVP |
| **브랜치** | `pivot/project-direction` |
| **검증 (당시)** | ruff · basedpyright · **pytest 14** |

#### 서비스 정의 (초기)
- 입력: 매장 유형·규모·객단가·행정동·상권·접근성 + 품목·일평균 소진 + (선택) 표준 LT/ROP
- 내부: 스코어링 + 결정론 KB + LT/ROP/CAPA 공식
- 출력: 한 줄 추천 · 비교 대시보드 · 근거 블록 (문서 예시 고정 출력 금지)
- UX: 폼 → 짧은 로딩 → 리포트

#### 주요 코드
| 경로 | 역할 |
|------|------|
| `app/pipeline/domain_catalog.py` | 옵션·라벨·채널 기본 LT |
| `app/pipeline/input/template.py` | 템플릿·검증·불일치 guidance |
| `app/pipeline/analyze/scoring.py` | CAPA/수요/접근성 가중치 |
| `app/pipeline/analyze/knowledge_base.py` | 행정동+품목 KB 시그널 |
| `app/pipeline/analyze/engine.py` | ROP·안전재고·CAPA 캡 |
| `app/pipeline/output/recommendation.py` | 비교표·근거 리포트 |
| `app/web/*` | 입력·로딩·결과 UI |

#### 아키텍처 요약
- 정본: `docs/architecture.md` · redesign 인덱스 링크

#### 한 줄
> 스켈레톤을 걷어내고, 플로우 문서에 적힌 ROP 재조정 제품을 결정론 파이프라인으로 채웠다.

---

### 2026-07-14 (월) 심야~ — ROP 운영 레버 정합 (국면 VII+) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | “LT는 가변 추천이 아니다”, 지도 유동, 현실적인 운영 레버 |
| **브랜치** | `pivot/project-direction` |
| **검증 (당시)** | ruff · basedpyright 0 · **pytest 30 passed** |
| **템플릿** | `rop-adjust-v1` **1.3.0** (→ 7/15에 1.3.1) |

#### 작업 묶음

| ID | 내용 | 핵심 산출 |
|----|------|-----------|
| **R7a** | 멀티 세션 입력 위저드 | `app/web` 환영→기본→세부→품목·운영 |
| **R7b** | 정확한 위치 + POI 유동지수 | Google Maps 시안 → **Kakao Local** 전환 (`geo_enrichment.py`) · `docs/setup-kakao-local.md` |
| **R7c** | foot_traffic 포화 완화 | 카테고리별 N캡 · 순위 감쇠 · soft_sat(raw/(raw+2.4)) · CS2=`convenience` 저가중 · 도심 혼합 ~0.5대 (과거 1.0 고정 해소) |
| **R7d** | LT 출력 고정 · 운영 레버 | **품목 LT 입력 유지** · 출력 delta=0 · 접근성/KB 리스크 → **버퍼 재고** · 비교표에 SS·Q·주기 |
| **R7e** | 서비스 레벨 · 발주 요일 | `service_level` 90/95/99 → 정책 Z · `order_day_pattern` 자동/화목/월수금 등 · 1회 발주량 Q 연동 |

#### 제품 공식 (7/14 당시 · 7/15에 SS 단위 정합 패치)

```
LT_input     = 품목 표준/계약 LT  (입력 유지 · 출력에서 변동 추천 없음)
Z            = SERVICE_LEVEL_Z[sl] + 맥락(변동성·품목·유동지수)
risk_days    = max(0, 접근성 + KB 상권·행정동 리스크)
buffer       = D * risk_days
SS           = Z * sqrt(LT * vol) * turnover + buffer   ← 7/15 이전: SS 통계항이 D 비비례
ROP          = D * LT + SS
(Q, 요일)    = 선택 패턴 또는 CAPA 자동 추천
CAPA 협소 시 ROP 상한 + 다회 소량 메시지
```

#### 핸드오프
- `handoff/2026-07-14-rop-service-build.md`
- `handoff/2026-07-14-foot-traffic-desaturation.md`
- `handoff/2026-07-14-lt-fixed-ops-levers.md`
- `handoff/2026-07-14-service-level-order-days.md`

#### 한 줄
> 매장이 **실제로 바꿀 수 있는 것**(ROP, 안전재고, 발주량, 요일, 서비스 레벨)에 추천을 모으고, LT는 품목 입력으로만 다룬다.

---

### 2026-07-15 (화) — 리뷰 권장 수정 · 정확도 패치 (국면 VIII) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | 브랜치 리뷰 P0/P1: 추천 정확도 · 비교표 오표시 · UX 회귀 · 테스트 공백 |
| **브랜치** | `cidtw/auto-run-1-20260715T0032` (pivot ROP 스냅샷 계열) |
| **검증** | `ruff` · `basedpyright app` 0 · **pytest 32 passed** |
| **템플릿** | `rop-adjust-v1` **1.3.1** |
| **핸드오프** | `handoff/2026-07-15-summary.md` |

#### 배경

7/14 VII+ 스냅샷 기준 코드 리뷰에서 **단위가 안 맞는 통계 SS**, **geo Z 과대 귀속**, **서비스 레벨 비교 1.65 하드코딩** 등이 정확도 위험으로 지적됐다.  
권장 수정(P0 → UX → 테스트 → Kakao 안정성)을 한 번에 반영했다.

#### 작업 묶음

| ID | 심각도 | 내용 | 핵심 산출 |
|----|--------|------|-----------|
| **R8a** | bug | 통계 SS를 **일평균 소진 비례**로 수정 | `store_safety_stock(..., daily_demand)` · `vol_norm=vol/5` |
| **R8b** | bug | geo 근거: Z 전체 델타 대신 **FTI boost만** 귀속 | `recommendation._geo_evidence` + `FOOT_TRAFFIC_Z_BOOST` |
| **R8c** | bug | 비교표 “서비스 레벨 Z” 표준 = **선택 정책 Z** (1.65 제거) | `_comparison` policy_z / context_z |
| **R8d** | UX | 발주 주기 표준이 LT 일수를 쓰지 않음 | auto→주1회 7일 · 고정 패턴→동일 cycle |
| **R8e** | UX | 폼 `standard_rop` prefill 제거 · API 에러 정규화 | `app/web/app.js` |
| **R8f** | 정책 | 미입력 LT·base SS 기본값 = **규모 밴드→채널** | `SIZE_TO_CHANNEL` · mismatch guidance 문구 |
| **R8g** | 안정성 | Kakao 인근 POI **병렬** + total budget 4s · HTTP 2.5s | `geo_enrichment.py` ThreadPoolExecutor |
| **R8h** | 테스트 | CAPA 무조건 assert · SS∝D · policy Z · size 기본값 · FTI 귀속 | `tests/test_pipeline.py` · `test_geo_enrichment.py` |

#### 제품 공식 (현행 · 7/15 이후)

```
LT_input     = 품목 표준/계약 LT  (입력 유지 · 출력에서 변동 추천 없음)
               미입력 시 SIZE_TO_CHANNEL[store_size] 채널 기본값
Z_policy     = SERVICE_LEVEL_Z[service_level]
Z            = Z_policy + 맥락(변동성·품목·시드·FOOT_TRAFFIC_Z_BOOST*fti)
risk_days    = max(0, 접근성 + KB 상권·행정동 리스크)
buffer       = D * risk_days
SS_stat      = Z * D * sqrt(LT * vol/5) * turnover     ← demand 비례
SS           = SS_stat + buffer
ROP          = D * LT + SS
(Q, 요일)    = 선택 패턴 또는 CAPA 자동 추천
비교표 cycle = auto면 주1회(7일) 기준 · 고정 패턴이면 선택 cycle
CAPA 협소 시 ROP 상한 + 다회 소량 메시지
```

#### 검증 기록

```
uv run ruff check app tests     # pass
uv run basedpyright app         # 0 errors
uv run pytest                   # 32 passed
```

#### 의도적으로 미룬 것

| 항목 | 비고 |
|------|------|
| 클라이언트 `AbortController` / 평가 취소 | 서버 budget으로 1차 완화 |
| Kakao fallback rate 메트릭·서킷 | 관측 인프라 이후 |
| hash-seed “품절 %” 서술 완화 | 캘리브레이션 오인 방지: 카피 작업 |
| R8 배포·환경 패리티 | Vercel · 시크릿 (기존 백로그) |

#### 한 줄
> 추천이 **수요 단위와 비교 라벨에서 틀어지지 않게** 고쳤다. 파이프라인 골격은 두고 공식·표시·테스트만 맞췄다.

---

### 2026-07-16 (수) — 안정화 픽스 · 추천 윤문 · 일시 유동 옵션 (국면 IX) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | pivot tip 리뷰 후속 버그픽스, UX 윤문, 일시 유동인구 증분 기능, 프로덕션 배포 |
| **브랜치** | `pivot/project-direction` (워크스페이스 `cidtw/auto-run-4-*`에서 tip 동기 후 푸시) |
| **배포** | Vercel production `https://md-preflight.vercel.app` (main 미변경: 아카이브) |
| **검증** | `ruff` · `basedpyright app` 0 · **pytest 46 passed** · wizard/export node smoke |
| **핸드오프** | `handoff/2026-07-16-summary.md` (gitignore · 로컬) |

#### 배경

- 푸시된 pivot tip(`6940c3a` 이후) 코드 리뷰에서 **CAPA Q clamp 저수요 버그**, **Q-only multi-order 문구 불일치**, geo shutdown soft budget, export 리스너 스택 위험이 지적됐다.
- 이어서 **추천 한 줄이 기계적**이라는 UX 피드백, **리포트 내보내기 무반응** 회귀, **일시 유동인구 옵션** 요구가 들어왔다.

#### 작업 묶음

| ID | 유형 | 내용 | 핵심 산출 |
|----|------|------|-----------|
| **R9a** | bug | CAPA Q: `max(1.0, round(max_cap))` 제거 → `order_qty = max_cap` | `engine.py` · 저수요 fixture |
| **R9b** | bug | Q-only multi-order 시 plain/tech CAPA가 「무리 없이」를 쓰지 않음 | `recommendation.py` · `multi_order_suggestion` 게이트 |
| **R9c** | UX | demand 카피 stockout index 분기 (넉넉히/보통/가볍게) | `knowledge_base.py` |
| **R9d** | 안정 | Kakao POI pool `shutdown(wait=False, cancel_futures=True)` | `geo_enrichment.py` |
| **R9e** | bug | export: 로드 시점 1회 bind 실패 → **result-panel 이벤트 위임** | `app/web/app.js` |
| **R9f** | UX | 추천 한 줄 plain/technical **문장형 윤문** (· 나열 제거) | `recommendation.py` |
| **R9g** | feat | **일시적인 유동인구 증가분 변수 고려** (세부 주소 전용) | 아래 R9g 상세 |
| **R9h** | docs | redesign pipeline SSOT · 본 일지 국면 IX | `docs/redesign/pipeline.md` · 본 파일 |

#### R9g — 일시 유동 옵션 (세션 2 매장 세부 정보)

| 항목 | 계약 |
|------|------|
| 파라미터 | `consider_temp_foot_traffic` (boolean, 선택) |
| 활성 조건 | `use_precise_location` + `store_address` 일 때만 UI 노출·서버 적용 |
| 검색 | 주소 지오코딩 후 **반경 200m** Kakao 키워드: 경기장·공연장·전시장·컨벤션 |
| 점수 | 시설 kind 가중 × `exp(-d/100)` × kind rank 감쇠 → soft-sat uplift ∈ [0,1] |
| 수요 | `D_eff = D × (1 + 0.35 × uplift)` (최대 약 +35%) |
| Z | `FTI_kb = min(1, FTI + 0.20 × uplift)` |
| 반영 | SS·버퍼·ROP·Q·CAPA에 `D_eff` · **표준 비교 기준은 행사 미반영 D** |
| 한계 | 실시간 행사 캘린더 없음 → **대형 유동 가능 시설 근접** 프록시 (근거 블록에 명시) |

주요 파일: `event_foot_traffic.py` · `geo_enrichment.py` · `engine.py` · `template.py` · `app/web/*` · `tests/test_event_foot_traffic.py`

#### 제품 공식 추가분 (현행 · 7/16 이후, VIII 위에 적층)

```
(옵션) event_uplift = soft_sat(Σ kind_w * exp(-d/100) * 0.5^rank)   # r=200m
(옵션) D_eff = D * (1 + 0.35 * event_uplift)   # 미옵션·시설 0이면 D_eff = D
buffer   = D_eff * risk_days
SS_stat  = Z * D_eff * sqrt(LT * vol/5) * turnover
ROP      = D_eff * LT + SS
Q        ≈ D_eff × cycle
CAPA     MaxCap·표시 SS도 D_eff 기준 항등
표준 비교 ROP/SS = 행사 미반영 D 기준
```

#### 커밋 계열 (pivot tip, 7/16)

| SHA (대표) | 메시지 요지 |
|------------|-------------|
| `ebe68f0` | CAPA Q clamp · multi-order evidence · export/geo polish |
| `b9ffe14` | 추천 plain/technical 문장형 윤문 |
| `aa8f9b2` | 리포트 내보내기 event delegation 복구 |
| (본 일지 커밋) | 일시 유동 옵션 + 국면 IX 일지 |

#### 검증 기록

```
uv run ruff check app tests     # pass
uv run basedpyright app         # 0 errors
uv run pytest                   # 46 passed
node scripts/verify_wizard_logic.mjs
node scripts/verify_report_export.mjs
vercel deploy --prod            # md-preflight.vercel.app
```

#### 한 줄
> **틀어지지 않는 숫자**에 **읽히는 추천 문장**, **깨지지 않는 내보내기**, 주소 기반 **일시 유동 수요 증분**까지 pivot 프로덕션에 올렸다.

---

### 2026-07-16 (수+) — 제3자 시연 준비 (국면 X / R14) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | 커밋 tip 리뷰 뒤, 외부 시연에 필요한 원클릭 프리셋·스모크·탭 폴리시 |
| **버전** | `0.3.3-rop` |
| **검증** | pytest **47** · node verify_demo_scenarios · `demo.sh` |

#### 작업
| ID | 내용 |
|----|------|
| **R14a** | 환영 화면 시연 시나리오 4종 (CAPA / 대형 / geo+event / mismatch) |
| **R14b** | `demo.sh` · `verify_demo_scenarios.mjs` |
| **R14c** | favicon · meta description · CORS prod · 버전 정합 |
| **R14d** | README 시연 절 · board Done · handoff |

#### 한 줄
> 숫자와 문장은 이미 시연 가능했던 제품에, **제3자가 바로 누르는 경로**를 붙였다.

---

### 이후 — ROP 고도화 (백로그)

| 항목 | 상태 | 비고 |
|------|------|------|
| R8 배포·환경 패리티 | **DONE (부분)** | Vercel prod 반복 배포 · Kakao 시크릿은 운영 문서 기준 |
| R9 실측 KB / 공공 데이터 | TODO | 현재 결정론 KB · 행사 스캔은 시설 프록시 · **XI에서 출처 표는 완료** |
| R9+ 실시간 행사 캘린더 | TODO | 공공/티켓 API 연동 시 event 프록시 교체 |
| R10 실 Agent AI 교체 | TODO | `knowledge_base.py` 포트 |
| R11 품목 마스터 연동 | TODO | |
| R12 발주 스케줄 캘린더 UX | TODO | 요일 패턴 시각화 |
| R13 클라이언트 타임아웃·취소 UX | TODO | AbortController |
| R14 stockout% 서술 캘리브 문구 | **DONE (부분)** | 상대 위험·인덱스 카피 (VIII/IX) · 잔여 폴리시는 선택 |
| **R15 산출 근거 패키지** | **DONE (문서)** | `docs/evidence/` · 문헌 매트릭스 · 스코프 축소 (국면 XI) |
| **R16 실측 σ·지연 경로** | **DONE (코드)** | `demand_sigma_daily` · `measured_logistics_delay_days` · source_layers UI · 시나리오 A 실측 |
| **R17 경쟁 포화** | **DONE** | `competition_saturation` · D_eff 곱 · 주소 전용 옵션 |
| **R18 what-if 시뮬** | **DONE** | `POST /api/simulate` · AI/폴백 대응 패널 · 단일 쇼크 모델 |
| **R19 데모 census** | **DONE** | 앵커 전수조사 스냅샷 · blob 임베드 · 분류기 정규화 91점 |
| **R20 P0 정합** | **DONE** | 리포트 D_eff · 이중적용 제거 · unmanned/hyper 픽스 |
| (구) T54/T55 v1 freeze | **SUPERSEDED** | v1 아카이브 · **main 변경 금지** |

---

## 4.x 국면 XI — 튜터 피드백 · 근거 심화 (2026-07-19)

### 피드백 요지

| # | 내용 | 대응 방침 |
|---|------|-----------|
| 1 | 아이템(ROP·LT 운영 레버 + 이중 UX)은 v1보다 훨씬 좋음 | **유지** |
| 2 | 시연 때 “실제 ROP/LT 산출 **객관 근거**”가 약해 보인다 | 문헌·기관 1차 출처 매핑 |
| 3 | 품목·매장 수를 줄여도 되니 **논리 완결**이 우선 | 스코프 축소 시나리오 고정 |

### 진단 (코드 기준)

- **강한 축**: \(ROP = D\cdot L + SS\), \(Z_{90/95/99}=1.28/1.65/2.33\), \(SS \propto Z\sqrt{L}\), LT 고정·지연→버퍼  
- **약한 축**: vol 1–5 σ proxy, 접근성 일수 테이블, hash logistics residual, soft-sat 계수, CAPA cover_days  
- 시연 리스크는 “식이 틀렸다”가 아니라 **계수 출처를 안 적어 둔 것**

### 산출물

| 경로 | 내용 |
|------|------|
| `docs/evidence/README.md` | 3층 답변 구조 (L1이론 · L2문헌 · L3 assumption) |
| `docs/evidence/literature-sources.md` | King/APICS PDF · ASCM · ROP 표준 · Huff · √L · 한계 문헌 |
| `docs/evidence/evidence-matrix.md` | **공식 항 ↔ 코드 ↔ 출처** SSOT 매트릭스 |
| `docs/evidence/parameter-ranges.md` | 계수 스케일 vs 문헌 관례 |
| `docs/evidence/demo-scope.md` | 매장 2 · 품목 2 고정 시연 체인 |
| `slide-outline.md` · `slides/` | 발표 아크에 근거·스코프 반영 |

### 핵심 1차 출처 (발표에서 이름 대기)

1. **Peter L. King, CSCP**: *Understanding safety stock…*, APICS 2011 (MIT 미러 PDF): Z 표 · \(SS=Z\cdot\sigma\sqrt{\cdot}\)  
2. **ASCM**: Safety stock / Z-factor 실무 인사이트  
3. **표준 ROP**: LTD + SS (실무 합의 · 교재 continuous review)  
4. **Huff (1964)**: 경쟁·거리 감쇠 형태  
5. Vandeput 등: 고전 식 한계 (정직 인용)

### 시연 한 문장 (국면 XI)

> 재주문점은 연속검토 표준식이고, Z는 King/APICS 표입니다.  
> 매장 변동·접근성 계수는 문헌 범위 안의 **명시적 proxy**입니다.  
> 품목·매장 수를 줄인 대신, 입력 → L1 → L2 → L3 → 숫자 체인을 끝까지 보여 드립니다.

### 의도적으로 안 한 것 (XI 문서 단계)

- 신규 공공 API 연동  
- main/v1 복원  

### 후속 구현 (같은 날 · R16 + 시나리오 A 실측)

| 항목 | 결과 |
|------|------|
| 시나리오 A evaluate | ROP **31.2** · SS **7.2** · Q **28** · 월수금 · raw 93.8 · CAPA cap · Z 1.65→2.38 |
| 전문 토글 | `source_layers` L1/L2/L3 카드 + export MD/PDF |
| R16 입력 | `demand_sigma_daily` · `measured_logistics_delay_days` (template v1.6.0) |
| 테스트 | `test_scenario_a_measured_walkthrough` · `test_r16_measured_sigma_and_delay` |

---

## 4.y 국면 XII — 상권·시뮬·정확도 정합 (2026-07-19 심야 ~ 07-20)

| 필드 | 내용 |
|------|------|
| **테마** | 경쟁 포화·what-if·데모 census를 제품에 넣고, **엔진 숫자와 UI/리포트 서사**를 맞춤 |
| **검증 (7/20 tip)** | `ruff` · `basedpyright app` 0 · **pytest 85** · `verify_competition_sim.mjs` |
| **핸드오프** | `2026-07-20-review-fixes.md` · `2026-07-20-p0-accuracy-ux.md` · 리뷰 아티팩트 P0 표 |

### 제품 확장 (R17–R19)

| 축 | 내용 |
|----|------|
| **경쟁 포화** | 정확한 주소 옵션 · 업종 반경 스캔 · intensity → `competition_demand_factor` (최대 −40%) · `D_eff = D × event × competition` |
| **what-if 시뮬** | `POST /api/simulate` · 4 시나리오(서비스 강화 / 경쟁 공세 / LT 스트레스 / 수요 반등) · 결정론 근사 |
| **매출 하락 조언** | 유효 수요 하락 시 xAI 고정 프롬프트 또는 **로컬 폴백** · UI `sim-ai-panel` 노출 (7/20) |
| **데모 census** | 앵커 세솔로 25 전수조사 · 스냅샷 JSON + **Vercel blob 임베드** · verified 카드 |

### P0 정확성 / UX (7/20 · 리뷰 권장 순서)

| # | 이슈 | 조치 |
|---|------|------|
| 1 | AI 조언 API 필드만 있고 UI 미표시 | `renderSimResult` 패널 + 스모크 |
| 2–3 | 리포트 ROP/SS/버퍼가 base D, 엔진은 D_eff | 식·plain 문구 D_eff 통일 |
| 4 | competitor_pressure −28% leak + 경쟁 스캔 이중 적용 | **수요 이탈 쇼크만** (계수 상속) |
| 5–6 | census 오분류 (프레시→hyper, 주차/미용 소음, 무인 할인점) | 분류기 강화 · 스냅샷 97→**91** |

### 불변 식 (발표용 한 줄)

> \(D_{\mathrm{eff}} = D \times m_{\mathrm{event}} \times f_{\mathrm{comp}}\)  
> \(ROP = D_{\mathrm{eff}}\cdot LT + SS\)  
> 경쟁 what-if의 “최대 약 −28%”는 **일 소진 이탈 쇼크**다. 상권 포화 계수와 두 번 곱하지 않는다.

### 의도적으로 남긴 것 (P1)

- evaluate/sim 시 Kakao 재호출 · AI 장시간 블로킹 → geo_override 재사용·타임박스  
- places/dong 프록시 rate limit  
- 이벤트 스캔 플래그 vs 경쟁 스캔 가드 비대칭  

---

## 4.z 국면 XIII — 최종 발표 전 UI 윤문 (2026-07-21) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | 시연 카드 가독성 · 레이아웃 · 교육과정 크레딧 (기능 로직 변경 없음) |
| **브랜치** | `pivot/project-direction` |
| **배포** | Vercel production `https://md-preflight.vercel.app` |
| **검증** | `ruff` · `basedpyright app` 0 · **pytest 89** |
| **제약** | **발표 초안·포스터 시안은 변경하지 않음** (일지·핸드오프·웹 UI만) |

### 피드백 대응 (발표 전날)

| # | 문제 | 조치 |
|---|------|------|
| 1 | `앵커` / `볼 포인트` / `residential` / `FTI` / `D=NN` 이 초심자에게 안 와닿음 | 카드 문구 평이 한국어화 (`대로변` · `주거지 밀착상권` · `유동 보통(0.53)` · `일 소진 약 N개` · `한눈에`) |
| 2 | 카드마다 `앵커 주소 전수조사(Kakao)` 반복 | 카드에서 제거 · 시연 블록 **상단 tech chip**으로 스택 표기 |
| 3 | PC에서 dense 리스트 2행이 애매하게 잘림 | `max-height: min(72vh, 760px)` + 카드 패딩·간격 축소로 2행 가시성 개선 |
| 4 | 교육과정·3기관 후원 미표기 | `coming-soon` 하단 `sponsor-credit` + 로고 3종 (기술학교·일자리재단·고양특례시) |

### 주요 파일

- `app/pipeline/demo_anchor_survey.py` — `surveyed_to_demo_cards` 평이 카피
- `app/web/index.html` · `app.js` · `styles.css` · `demo_scenarios.mjs`
- `app/web/logos/{gts,gjf,goyang}-logo.png`
- `tests/test_demo_anchor_survey.py` — 평이 카피·노트 필터 회귀

### 의도적으로 안 한 것

- `slide-outline.md` · `slides/` · `decks/` · A3 포스터 시안 수정
- 엔진·스코어링·census 스냅샷 재수집

### 한 줄
> **기능은 그대로**, 시연 첫 화면만 **처음 보는 사람이 읽을 수 있게** 다듬고 교육 크레딧을 붙였다.

---

## 5. 발표용 스토리 스크립트

### 5.1 30초
> 7월에 유통 **프로모션 사전검수 v1**을 엔진부터 Vercel 라이브까지 올렸고, 중간발표 뒤에는 입력 유연성까지 다듬었습니다.  
> 피드백을 받은 뒤 v1은 태그로 아카이브하고, **매장 특화 발주 기준(ROP) 재조정**으로 방향을 바꿨습니다.  
> 리드타임은 품목 입력으로 그대로 두고, 실제로 조정하는 것은 ROP, 안전재고, 발주 요일, 서비스 레벨입니다.  
> 문헌 근거(L1–L3)와 좁은 시연으로 논리를 보강했고, 이어서 **경쟁 포화·what-if 시뮬**과 **식과 서사 정합**까지 맞췄습니다.

### 5.2 2분 (국면별)
1. **엔진(v1 / main)**: 판정은 룰, LLM은 설명. 계약 테스트로 증명.  
2. **워크스페이스·라이브(v1)**: SPA, Clerk/Neon, degrade, pytest 132→150.  
3. **피드백(v1)**: 별칭, 4화면, 어댑터(T48–T59).  
4. **피벗**: `archive/v1-md-preflight`, 3단 파이프라인.  
5. **ROP 제품**: 파라미터 → 점수·KB·Kakao 유동 → 근거 리포트, 운영 레버.  
6. **정확도 패치(7/15)**: SS∝수요, 비교표 Z/주기, size 기본값, CAPA/geo 테스트.  
7. **안정화·일시 유동(7/16)**: CAPA/Q, 추천 윤문, export 복구, 200m 행사 수요 증분, Vercel.  
8. **근거 심화(7/19)**: King/ASCM/Huff 매핑, L1–L3, 매장 2·품목 2 시연.  
9. **상권·시뮬·정합(7/20)**: 경쟁 포화, what-if + 하락 조언 UI, census, D_eff 서사.

### 5.3 5분
위에 시나리오 A 실측 워크스루를 붙입니다.  
LTD=24 → Z 1.65→2.38 → raw ROP 93.8 → **CAPA 31.2 / SS 7.2 / Q 28 / 월수금**  
여기에 전문 토글 **L1/L2/L3 카드**와, 가능하면 R16 σ 입력 데모를 보여 줍니다.  
시간이 되면 **경쟁 공세 시뮬**을 한 번 눌러 유효 수요 −%, ROP/Q 재조정, 폴백 대응 패널까지 갑니다.  
발표 장표는 **`slide-outline.md`**, 숫자 SSOT는 **`docs/evidence/demo-scope.md`**입니다.

### 5.4 질의 예상 — “근거가 뭐냐?”

| 질문 | 답 축 |
|------|--------|
| ROP 식이 맞나? | L1 continuous review: \(D_{\mathrm{eff}}\cdot LT+SS\) |
| 1.65는? | King/APICS CSL 95% Z |
| 왜 √LT? | 독립 기간 분산을 합치면 σ√L |
| 왜 ROP가 31이지 93이 아니야? | CAPA MaxCap 12×2.6=31.2. 표시 SS 7.2로 항등 유지, 다회 소량 |
| 골목/건물내 일수? | L3 engineering. R16 실측 지연 입력 시 대체 |
| 행정동 hash? | proxy_kb. **캘리브레이션이 아님**. measured_logistics_delay_days로 줄임 |
| POS σ 있으면? | `demand_sigma_daily` → measured_sigma 경로 |
| 경쟁 −28%는? | what-if **일 소진 이탈** 상한. 상권 포화 계수와 **이중 적용 안 함** (XII) |
| 데모 점포 숫자는? | 앵커 census 스냅샷(정규화 후 91). 라이브 재조사는 키·쿼터 가드 |

---

## 6. 참고 문서 인덱스

| 주제 | 경로 |
|------|------|
| **리빌드 아키텍처 요약 (정본)** | `docs/architecture.md` |
| **산출 근거 패키지 (국면 XI)** | `docs/evidence/` |
| **근거 매트릭스 SSOT** | `docs/evidence/evidence-matrix.md` |
| **문헌 목록** | `docs/evidence/literature-sources.md` |
| **시연 스코프** | `docs/evidence/demo-scope.md` |
| **P0 정합 handoff (국면 XII)** | `handoff/2026-07-20-p0-accuracy-ux.md` |
| **재설계 지시** | `2026-07-14-Project-Redesign.md` |
| **ROP 서비스 플로우** | `2026-07-14-New-Service-Flow.md` |
| **재설계 판** | `docs/redesign/` |
| **Kakao Local 설정** | `docs/setup-kakao-local.md` |
| **최종 발표 아웃라인 (slides-grab)** | `slide-outline.md` |
| **v1 아카이브** | `archive/v1-md-preflight/` · tag `archive/v1-md-preflight` |
| v1 설계·룰·ADR·샘플 (트리 삭제) | tag `archive/v1-md-preflight` (`git show …:PATH`) |
| pivot 이후 handoff | `handoff/2026-07-14*` ~ `2026-07-21*` |
| pre-pivot handoff 백업 | `handoff/archive-v1-pre-pivot-20260720.tar.gz` (gitignore) |

---

## 7. 작성 규칙

1. **기능 커밋/배포 후** 해당 일자 행과 티켓·보드를 갱신한다.  
2. 수치는 **그 세션에서 돌린 pytest**를 우선한다. 과거 스냅샷은 “참고”로만 쓴다.  
3. `handoff/`는 gitignore다. **발표용 정본은 본 `docs/` 파일**과 `slide-outline.md`다.  
4. 신규 국면이 생기면 §0 아크 다이어그램에 한 줄만 추가한다.  
5. **국면 VI 이후** 활성 아키텍처 정본은 `docs/architecture.md`, 계약·보드는 `docs/redesign/`이다. v1 문서·샘플은 태그 `archive/v1-md-preflight` 에서 확인한다.  
6. 스코어링/KB/지도/운영 레버를 바꾸면 테스트, 일지, `docs/architecture.md`, 필요 시 `slide-outline.md`를 함께 갱신한다.

---

*정본 경로: `docs/dev-journal-2026-07.md`*  
*최초 작성(7/14 구간): 2026-07-14 · 전체 흐름 통합: 2026-07-14 (7/1–13 소급 정리)*  
*국면 VI 재설계 준비 반영: 2026-07-14*  
*국면 VII ROP 서비스 빌드 반영: 2026-07-14*  
*국면 VII+ 운영 레버·일지/발표 아웃라인 갱신: 2026-07-14*  
*국면 VIII 정확도 패치(리뷰 권장 수정) 반영: 2026-07-15*  
*국면 IX 안정화·일시 유동·배포 반영: 2026-07-16*  
*국면 X 제3자 시연 준비(R14): 2026-07-16*  
*국면 XI 튜터 피드백·근거 패키지(R15)·발표 반영: 2026-07-19*  
*시나리오 A 실측 · source_layers UI · R16 실측 경로: 2026-07-19*  
*국면 XII 상권·시뮬·census · P0 D_eff/UI/분류기 정합 · 일지·발표 초안: 2026-07-20*  
*국면 XIII 최종 발표 전 UI 윤문(카드 평이화·스크롤·교육 크레딧) · 발표/포스터 미변경: 2026-07-21*
