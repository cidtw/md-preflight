# MD Preflight 개발 일지 — 2026년 7월 전체 흐름

> **용도**: 최종 발표 시 “무엇을 언제·왜 만들었는가”를 **7/1 착수 → 7/13 중간발표 → 7/14 피드백 → 방향성 재설계**까지 한 줄기로 설명하기 위한 정본.  
> **범위**: 2026-07-01 ~ (진행 중; 국면 VI 재설계 포함)  
> **근거**: git 커밋 · `handoff/` 노트 · 티켓 T1~T59 · 재설계 지시 `2026-07-14-Project-Redesign.md` · 당일 검증 수치  
> **관련**: `docs/redesign/` · `archive/v1-md-preflight/` · `docs/architecture-easy.md` (v1) · `BACKEND_ARCHITECTURE.md` (v1 archived)

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
[7/14 eve] ROP 제품화   매장 파라미터 → LT/ROP 추천 · 근거 리포트 (국면 VII)
```

| 국면 | 기간 | 한 줄 목표 | 대표 산출 |
|------|------|------------|-----------|
| **I. 엔진 코어** | 7/1–4 | 결정론 검수가 돌아가게 | 10룰 · ingest · API · D3 계약 |
| **II. MD 워크스페이스** | 7/5–6 | 브라우저에서 쓰고 고치게 | SPA · 편집 · 체크리스트 · 테마 |
| **III. 라이브 제품** | 7/7–9 | 프로덕션에서 안 죽게 | Clerk/Neon/LLM · degrade · harden |
| **IV. 발표 품질** | 7/9–13 | 스토리·데모가 안 깨지게 | 덱 · seed · 스모크 · 모듈 분리 |
| **V. 중간발표 이후** | 7/14 오전 | 약점(고정 컬럼·한 화면) 해소 | T48–T59 · UI 리프레시 |
| **VI. 방향성 재설계** | 7/14 오후 | v1 동결 · 모듈 3단 판 | archive · pipeline skeleton |
| **VII. ROP 서비스** | 7/14 저녁~ | 매장 특화 LT/ROP 재조정 제품화 | scoring · KB · report UI |

**불변 원칙**

| 구간 | 원칙 |
|------|------|
| **국면 I–V (v1, D3)** | 판정 = 결정론 룰 · 서술 = LLM(실패 시 fallback) · 검수 비로그인 200 · 이력은 격리·append-only |
| **국면 VI+ (재설계)** | 판정 = 결정론 **가중치 점수** · 입력 = 파라미터 템플릿 · 출력 = **한 줄 recommendation** · 스테이지 모듈 추가만 허용 · 실 가중치는 조사 후 주입 (R0–R2 선행) |

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
| R7+ | 배포·실 KB·실 Agent | 이후 | **TODO** |

---

## 2. 지표 궤적 (대략)

| 시점 | pytest (참고) | 제품 상태 |
|------|---------------|-----------|
| 7/2 전후 | 초기 스위트 | 룰 확장·서비스 분리 |
| 7/4 상태 스냅샷 | **47** | T1–T12 핵심 엔진 거의 완료 |
| 7/9 T42/T43 | **104** | 프로덕션 hardening 직전·직후 |
| 7/9–10 덱/폴리시 | **132** | 발표 KPI로 고정 |
| 7/14 T48–T51 | **141–142** | 별칭·라우트·UI |
| 7/14 T52–T53 | **143** | catalog + error UX |
| 7/14 T56–T59 | **150** | v1 입력 어댑터 피크 (아카이브 기준점) |
| **7/14 재설계 스켈레톤** | **12** | 파이프라인 unit/API only (의도적 슬림) |
| **7/14 ROP 서비스** | **14** | LT/ROP 엔진 · 불일치 guidance · 리포트 UI |
| 이후 | green + R7+ | 배포·실 KB 확장 |

---

## 3. Part A — 7/1 ~ 7/13 빌드 과정

### 2026-07-01 ~ 07-02 (화–수) — 프로젝트 착수 · 룰 확장

| 필드 | 내용 |
|------|------|
| **테마** | “프로모션 사전검수” 코드베이스 기동 |
| **핵심 커밋** | `5050e23` Initial commit · 마진/재고 룰 추가 계열 |
| **산출** | FastAPI 골격 · 초기 룰 세트 · fallback 서술·리포트 서비스 분리 시작 |
| **핸드오프** | `2026-07-02-mvp-rule-expansion.md` · `2026-07-02-workspace-smoke-test.md` |

**한 줄**  
> 유통 등록 전 검수라는 문제를 **결정론 룰 엔진**으로 풀겠다는 방향을 코드에 박기 시작.

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
> **“같은 입력 → 같은 이슈”** 와 **“LLM은 서술만”** 이 코드·테스트·문서로 동시에 잠긴 날.

---

### 2026-07-05 (토) — 발표 초안 · 제품 카피

| 필드 | 내용 |
|------|------|
| **테마** | 개발 초안 발표 덱·카피 폴리시 (제품 스토리 정리) |
| **핸드오프** | `2026-07-05-dev-draft-presentation-*` |
| **의미** | 기술 구현과 별도로 **청중 언어**로 문제·해결을 고정 |

---

### 2026-07-06 (일) — MVP 프론트엔드 폭발적 확장 (Phase II)

| 필드 | 내용 |
|------|------|
| **테마** | 브라우저에서 업로드→검수→수정→재검수 루프 완성 |
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
> 백엔드 엔진 위에 **MD가 실제로 만지는 워크스페이스**가 하루 만에 올라왔다.

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
> “데모 가능한 로컬 앱”에서 **라이브 SaaS 스택**으로 승격. 중간발표의 기술 데모 바닥이 깔림.

---

### 2026-07-08 (화) — 네트워크·실환경 점검

| 필드 | 내용 |
|------|------|
| **테마** | 프로덕션 경로 관측 · E132 네트워크 체크 등 운영 이슈 핸드오프 |
| **핸드오프** | `2026-07-08-E132-Network-Check-Handoff.md` |
| **의미** | 배포 직후 **실환경 마찰**을 티켓/노트로 남김 |

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
> 기능을 더 넣기보다 **안 깨지는 라이브 + 한 번에 읽히는 덱**에 투자.

---

### 2026-07-10 (목) — 데모 신뢰성 데이

| 필드 | 내용 |
|------|------|
| **테마** | 프로덕션 health · seed · LLM 스모크 · 덱 날짜 7/13 |
| **핸드오프** | `2026-07-10-summary` · `day07-demo-reliability` |
| **완료** | health clerk/postgres · 비로그인 검수 · 이력 401 · Neon seed · 모델 ID 확증 |
| **잔여** | Clerk **실브라우저** e2e (사용자 액션) · 발표 계정 seed 정합 |

**한 줄**  
> 발표 전 “라이브 경로가 죽지 않는다”를 API 레벨에서 다시 못 박음.

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
| **의미** | 단일 `app.js` 거대 파일을 모듈로 분해 → **7/14 이후 UX 개편의 발판** |

**중간발표에서 드러난 것 (→ Part B 입력)**
1. 고정 csv/xlsx · 고정 컬럼에 대한 질문  
2. 교육 시간·타겟 유저  
3. **column key 변경 미테스트**  
4. 자가진단: 실무 edge · SPA 한 덩어리 · Clerk 테스트 마찰  

**한 줄**  
> 제품은 라이브·검증 완료 상태로 발표. 피드백은 **다음 스프린트 백로그의 입구**가 됨.

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
| **테마** | 중간발표 약점 2축(고정 컬럼·한 화면)을 **수정 가능 빌드**로 해소 |
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
> 중간발표가 남긴 구멍을 final RC 전체가 아니라 **ingest 유연성 + 화면 구조 + 설정 SSOT**로 닫았다. 판정 경계(D3)는 유지.

#### 1.12 연속 세션 — T56–T59 (입력 어댑터 X/Z)

| 항목 | 내용 |
|------|------|
| **결정** | X/Z 채택 — 정규 3프레임 유지, 어댑터로 입력 개방 (Y 폐기) |
| **T56** | ADR `docs/adr/0001-input-adapter-canonical-frames.md` · Frame/Role/Mapping 용어 |
| **T57** | N파일 업로드 · `POST /detect-roles` · 역할 매핑 UI |
| **T58** | 멀티시트 xlsx 시트 단위 아티팩트 분리 · `promotion_sheet` 등 선택자 · `multisheet` 샘플 |
| **T59** | `role_mappings` 폼 → Report/MD/결과 UI 감사 기록 |
| **커밋** | `8c38c20` (T56–57) · `ded69df` (T58–59) · pytest **150** |

---

### 2026-07-14 (월) 오후 — 방향성 재설계 준비 (국면 VI) **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | 프로젝트 방향성 자체 변경 — v1 아카이브 + 모듈 3단 파이프라인 판 제작 |
| **지시문** | `2026-07-14-Project-Redesign.md` |
| **브랜치** | `pivot/project-direction` (remote tracking) |
| **아카이브 태그** | `archive/v1-md-preflight` → commit `b444be0` |
| **검증** | `ruff` pass · `basedpyright app` 0 errors · **pytest 12 passed** |

#### 피드백/문제 인식 (지시 §1)

1. **기능 과다** — 10룰·어댑터·Clerk/Neon·대형 SPA가 한 제품에 공존  
2. **서비스 근거 빈약** — 조사 기반 평가 가중치·추천 논리가 제품 중심에 없음  
3. **가벼운 서비스 + 무거운 웹** — 본체 대비 웹표준·프로덕션 표면이 체감 부하를 키움  

#### 방향 재설정 (지시 §2)

1. 좁은 스코프 · 논리·근거 명확  
2. 파라미터 입력 → 사전 조사 가중치 분석 → **한 줄 recommendation**  
3. 명확 프레임워크 · 간결 구조 · 환경 무관 동일 경험  
4. 블록·모듈형으로 이후 기능 추가  

> **서비스 세부 구성(도메인·실 가중치·본 UI)은 준비 과정 완결 후** — board R0+ 에서 진행.

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
| `BACKEND_ARCHITECTURE.md` / `DESIGN.md` | **ARCHIVED v1** 배너 |
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
> v1은 **태그로 완전히 동결**하고, 활성 트리는 “파라미터 → 가중치 → 한 줄 추천”만 남는 **빈 판**으로 리셋했다. 다음 일은 코드가 아니라 **근거(R0–R2)** 다.

#### 의도적으로 하지 않은 것 (지시 준수)

- 실 서비스 도메인·조사 가중치 확정 (board R0+ **NOT STARTED**)  
- 본격 UI 폴리시·프레임워크 선정  
- v1 기능을 새 파이프라인에 억지 이식  

---



### 2026-07-14 (월) 저녁 — ROP 서비스 플로우 빌드 **DONE**

| 필드 | 내용 |
|------|------|
| **테마** | `2026-07-14-New-Service-Flow.md` 기준 매장 특화 LT/ROP 재조정 구현 |
| **브랜치** | `pivot/project-direction` |
| **검증** | ruff pass · basedpyright 0 · **pytest 14 passed** |

#### 서비스 정의
- 입력: 매장 유형·규모·객단가·행정동·상권·접근성 + 품목·일평균 소진 + (선택) 표준 LT/ROP
- 내부: 스코어링 테이블 + 결정론 KB 매칭 + 공식 (LT/ROP/CAPA 상한)
- 출력: 한 줄 추천 · 비교 대시보드 · 근거 3블록 (문서 예시 문장 고정 출력 금지)
- UX: 폼 → 짧은 로딩 → 리포트 (2단계는 내부 전용)

#### 주요 코드
| 경로 | 역할 |
|------|------|
| `app/pipeline/domain_catalog.py` | 옵션·라벨·채널 기본 LT |
| `app/pipeline/input/template.py` | 템플릿·검증·불일치 guidance |
| `app/pipeline/analyze/scoring.py` | CAPA/수요/접근성 가중치 |
| `app/pipeline/analyze/knowledge_base.py` | 행정동+품목 KB 시그널 |
| `app/pipeline/analyze/engine.py` | 추천 LT/ROP · CAPA 캡 |
| `app/pipeline/output/recommendation.py` | 비교표·근거 리포트 |
| `app/web/*` | 입력 폼·로딩·결과 UI |

#### 보드
R0–R6 **DONE** · R7+ (배포·실 KB·실 Agent) backlog

#### 한 줄
> 스켈레톤 quality/cost/risk 를 걷어내고, 플로우 문서의 ROP 재조정 제품을 결정론 파이프라인으로 채웠다.
#### 아키텍처 요약 발행
- 정본: `docs/architecture.md` (전체 구조 · 3단 파이프라인 · 공식 · 코드맵 · 배포 · v1 경계)
- README / redesign 인덱스 링크 추가


### 2026-07-15 이후 — ROP 고도화 (예정)

| 항목 | 상태 | 비고 |
|------|------|------|
| R7 배포·환경 패리티 | TODO | Vercel |
| R9 실측 KB / 공공 데이터 | TODO | 현재 결정론 KB |
| R10 실 Agent AI 교체 | TODO | `knowledge_base.py` 포트 |
| R11–R12 품목 마스터·발주 스케줄 | TODO | |
| (구) T54/T55 v1 freeze | **SUPERSEDED** | v1 아카이브 |

> 국면 VII에서 ROP MVP 동작. 다음 확장은 실데이터 KB·배포.

---

## 5. 발표용 스토리 스크립트

### 5.1 30초 (국면 VI 반영)
> 7월에 유통 프로모션 사전검수 v1을 엔진부터 라이브까지 올렸고, 중간발표 뒤 입력 유연성까지 다듬었습니다.  
> 피드백 후 v1은 아카이브하고, **매장 특화 Lead Time / ROP 재조정**(파라미터 → 내부 점수·KB → 근거 리포트)으로 방향을 바꿨습니다.

### 5.2 2분 (국면별)
1. **엔진(v1)** — 판정은 룰, LLM은 설명. 계약 테스트로 증명.  
2. **워크스페이스·라이브(v1)** — SPA, Clerk/Neon, degrade.  
3. **피드백(v1)** — 별칭·4화면·어댑터(T48–T59).  
4. **피벗·ROP** — 태그 아카이브 후 매장 파라미터 기반 LT/ROP 추천과 근거 3블록.

### 5.3 5분
위 + CAPA 상한·불일치 guidance · `POST /api/evaluate` 데모 · 결정론 KB vs 향후 실 Agent 로드맵.

---

## 6. 참고 문서 인덱스

| 주제 | 경로 |
|------|------|
| **재설계 지시** | `2026-07-14-Project-Redesign.md` |
| **재설계 판** | `docs/redesign/` |
| **v1 아카이브** | `archive/v1-md-preflight/` · tag `archive/v1-md-preflight` |
| 쉬운 아키텍처 (v1) | `docs/architecture-easy.md` |
| 백엔드 설계 (v1 archived) | `BACKEND_ARCHITECTURE.md` |
| 룰 매트릭스 (v1) | `docs/rule-matrix.md` |
| 입력 어댑터 ADR (v1) | `docs/adr/0001-input-adapter-canonical-frames.md` |
| 7/14–24 플랜 (v1, superseded) | `handoff/2026-07-14-plan-through-0724.md` |
| 7/9–13 재플랜 | `handoff/2026-07-09-replan-through-0713.md` |
| 중간발표 피드백 | `handoff/tickets/2027-07-14-AFTER-MIDTERM-REVIEW-PLAN.md` |
| 티켓 원문 (v1) | `handoff/tickets/T*.md` |
| 일자 handoff | `handoff/2026-07-*.md` |

---

## 7. 작성 규칙

1. **기능 커밋/배포 후** 해당 일자 행과 티켓/보드를 갱신한다.  
2. 수치는 **그 세션에서 돌린 pytest** 를 우선한다 (과거 스냅샷은 “참고”).  
3. `handoff/` 는 gitignore — **발표용 정본은 본 `docs/` 파일**.  
4. 신규 국면이 생기면 §0 아크 다이어그램에 한 줄만 추가한다.  
5. **국면 VI 이후** 활성 계약 문서는 `docs/redesign/` 이며, v1 문서는 아카이브 배너를 유지한다.  
6. 실 평가 가중치는 조사(R0–R2) 없이 코드에 박지 않는다.

---

*정본 경로: `docs/dev-journal-2026-07.md`*  
*최초 작성(7/14 구간): 2026-07-14 · 전체 흐름 통합: 2026-07-14 (7/1–13 소급 정리)*  
*국면 VI 재설계 준비 반영: 2026-07-14*
*국면 VII ROP 서비스 빌드 반영: 2026-07-14*
