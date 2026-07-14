# MD Preflight 아키텍처 — 쉽게 설명하기

> **한 줄**: 임의 업로드를 **정규 3프레임(행사·상품·재고)으로 정제**한 뒤 **규칙 엔진이 판정**하고, **LLM은 그 결과만 말로 풀어** 리포트·체크리스트를 만든다.  
> **불변 원칙 (D3)**: 판단 = 결정론 룰 · 서술 = LLM(실패 시 fallback) · 검수는 로그인 없이도 동작.  
> **입력 전략 (X/Z)**: 프레임은 유지, 어댑터로 개방 — `docs/adr/0001-input-adapter-canonical-frames.md`

---

## 1. 엘리베이터 피치 (30초)

유통 MD가 프로모션을 **등록하기 전**에  
프로모션 계획 · 상품 마스터 · 재고 파일을 올리면,  
시스템이 **가격·기간·마진·재고·증정** 리스크를 자동으로 짚어 준다.

- 같은 파일 → **항상 같은 이슈** (감사·재현 가능)
- AI는 “왜 위험한지” 설명만 하고, **pass/fail을 바꾸지 않음**
- ERP마다 컬럼명이 달라도 **별칭으로 정규 키에 수렴**

---

## 2. 전체 그림 (두 갈래)

시스템을 **두 경로**로 나누면 설명이 쉽다.

```
┌─────────────────────────────────────────────────────────────┐
│  A. 무상태 판정 경로  (검수의 본체 · 항상 살아야 함)            │
│                                                             │
│   업로드 3파일                                                │
│      │                                                      │
│      ▼                                                      │
│   ingest (읽기 → 별칭 수렴 → 정규화 → 조인)                    │
│      │                                                      │
│      ▼                                                      │
│   PreflightContext                                          │
│      │                                                      │
│      ▼                                                      │
│   Rule Engine (룰 10개, 순수 함수)  →  list[Issue] + 요약     │
│      │                                                      │
│      ├─ use_llm=true  →  LLM 서술 (OpenAI/Anthropic)         │
│      └─ 실패/OFF      →  Fallback 서술 (로컬 템플릿)          │
│      │                                                      │
│      ▼                                                      │
│   PreflightReport  (JSON · Markdown)                        │
└─────────────────────────────────────────────────────────────┘
                         │ 저장 실패해도 검수 200 유지
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  B. 격리된 이력·인증 경로  (있으면 좋고, 없어도 검수는 됨)      │
│                                                             │
│   RunStore (run_id → 리포트)     Postgres 또는 메모리         │
│   HistoryStore (유저별 집계)     Postgres 또는 메모리         │
│   Clerk / stub / off           이력·대시보드만 보호           │
└─────────────────────────────────────────────────────────────┘
```

| 경로 | 하는 일 | 죽으면? |
|------|---------|---------|
| **A 판정** | 업로드→룰→리포트 | 서비스 본질 상실 → 절대 degrade 없이 동작 |
| **B 이력** | 저장·대시보드·로그인 | DB/Clerk 장애 시 **인메모리/비로그인**으로 내려감 |

---

## 3. 요청 한 건의 흐름 (60초 데모 스크립트)

```
1. 브라우저/API
   POST /api/preflight
   + promotion_plan, product_master, inventory
   + use_llm=true|false

2. routes.py  (얇은 진입점)
   · 확장자·크기 검사
   · validation_engine 호출

3. ingest
   loader     : csv/xlsx → DataFrame
   aliases    : 상품코드·행사가 등 → product_code·promo_price
   normalize  : 타입 캐스팅 + promotions ⋈ master ⋈ inventory
               → PreflightContext (+ column_mappings)

4. rules (10개)
   각 룰: Context → list[ValidationIssue]
   한 룰이 터져도 다른 룰은 계속 (failed_rules에만 기록)

5. 서술
   LLM 또는 Fallback → ai_summary, checklist

6. 조립
   PreflightReport
   · issues, summary, column_mappings
   · rule_set_version (룰+임계값 해시)

7. (부가) 저장
   run_store.save / history_store.append
   · 실패해도 리포트는 이미 완성 → 200

8. UI
   #/run 결과 · 매핑 표 · 체크리스트 · MD 다운로드
```

---

## 4. 폴더 = 역할 (암기 맵)

```
app/
├─ main.py          앱 생성, /, /static, /samples
├─ api/             HTTP만 (routes + deps) — 비즈니스 로직 없음
├─ core/            Settings, 에러, 룰 임계값
├─ domain/          컬럼 정본 · 별칭 · PreflightContext
├─ ingest/          파일 읽기 · 정규화 · 조인
├─ rules/           ★ 심장 — 룰 1파일 = 1판정
├─ services/        엔진 오케스트레이션 · LLM · 저장 · 리포트
├─ schemas/         API 계약 (Issue, Report, History)
├─ sources/         외부 소스 카탈로그 스텁
└─ web/             SPA (해시 라우트 4화면, 빌드 스텝 없음)
```

**설명 팁**  
“백엔드는 **파이프라인**이고, 프론트는 **같은 오리진 static SPA**입니다.  
복잡한 마이크로서비스가 아니라 **한 FastAPI 프로세스** 안에 판정·서빙이 같이 있습니다.”

---

## 5. 핵심 객체 3개

| 객체 | 비유 | 내용 |
|------|------|------|
| **PreflightContext** | 시험지 + 채점 기준표 | 정규화된 3표 + `joined` + 임계값 + 컬럼 매핑 |
| **ValidationIssue** | 빨간 펜 지적 | code, severity, 위치(file/row/col), 관측/기대/제안 |
| **PreflightReport** | 성적표 | 이슈 목록 + 요약 + 체크리스트 + 매핑 + 버전 + run_id |

룰 개발자 관점:

```text
입력:  PreflightContext  (이미 조인 끝)
출력:  list[ValidationIssue]
부수효과: 없음  (순수 함수에 가깝게)
```

룰 추가 비용:

```text
1) app/rules/새룰.py
2) RULES 리스트에 1줄
→ 끝. 플러그인 로더/DSL 없음.
```

---

## 6. 왜 LLM에 판정을 안 맡기는가 (발표 Q&A)

| 문제 | LLM 판정 시 | 우리 설계 |
|------|-------------|-----------|
| 재현 | 같은 파일도 실행마다 다를 수 있음 | 룰 = 같은 입력 같은 이슈 |
| 환각 | 없는 오류·누락 가능 | 이슈는 코드가 확정 |
| 감사 | “왜 통과?” 설명 불가 | code + location + rule_set_version |
| 보안 | 프롬프트로 판정 조작 가능 | LLM은 **이미 확정된 summary/issues만** 입력 |

**비유**: 룰 엔진 = 회계 감사 프로그램, LLM = 감사 결과를 한국어로 읽어 주는 아나운서.

---

## 7. 프론트 아키텍처 (짧게)

| 항목 | 내용 |
|------|------|
| 형태 | FastAPI가 `index.html` + `/static/*` 서빙 (번들러 없음) |
| 라우트 | 해시: `#/` 홈 · `#/run` 결과 · `#/dashboard` 이력 · `#/settings` 설정 |
| 상태 | 브라우저 메모리 (업로드·편집·결과). 새로고침 시 결과 라우트는 홈으로 폴백 |
| 인증 UI | Clerk(실서버) / stub(로컬) / off — **검수 버튼은 비로그인도 활성** |
| 설정 | 별칭 카탈로그·업로드 한도 **읽기 전용** 안내 |

---

## 8. 외부 의존성 (켜지면 무엇이 바뀌나)

| 환경 변수 / 서비스 | 모드 | 효과 |
|--------------------|------|------|
| 없음 | degrade | LLM fallback · 메모리 저장 · 인증 off |
| OpenAI / Anthropic 키 | 서술 강화 | `generated_by=llm` 가능, 실패 시 자동 fallback |
| `DATABASE_URL` (Neon) | 이력 실속 | run/history Postgres |
| Clerk 키 | 로그인 | 대시보드·소유 run 보호 |

**설명 한 줄**: “프로덕션은 Clerk+Neon+LLM이 붙지만, **뼈대는 키 없이도 동작**하도록 설계했다.”

---

## 9. 데이터·정합성 규칙 (면접/테크리드용 한 스푼)

1. **조인 1:1**  
   프로모션 행 수 = joined 행 수. 깨지면 `IngestError`.
2. **마스터/재고 중복 코드**  
   조인 입력에서는 first-row dedup, 중복 자체는 `DUPLICATE_MASTER_CODE` 경고.
3. **별칭**  
   `app/domain/column_aliases.py` 표로만 수렴 (fuzzy ML 없음 → 결정론 유지).
4. **원본 PII 미저장 정책**  
   이력은 집계·메타 중심, 판정 경로와 저장 경로 격리.

---

## 10. 발표용 다이어그램 (슬라이드 복붙)

### 10-A. 레이어

```
[ UI SPA ]  →  [ API ]  →  [ Ingest ]  →  [ Rules ]  →  [ Narrative ]
   web/         routes      loader         rules/*       llm_service
                deps        aliases        RULES[]       fallback
                            normalize                    report_service
                                         ↓
                                   PreflightReport
                                         ↓
                              RunStore / HistoryStore (optional)
```

### 10-B. “무엇이 진실 원천인가”

| 관심사 | SSOT (정본) |
|--------|-------------|
| 기대 컬럼 | `domain/columns.py` |
| 헤더 별칭 | `domain/column_aliases.py` |
| 룰 목록 | `rules/__init__.py` → `RULES` |
| 임계값 | `core/rule_config.py` / Settings |
| 업로드 한도 | Settings → HTML `__MDP_CONFIG__` |
| API shape | `schemas/*` |

---

## 11. 자주 나오는 질문 치트시트

**Q. 마이크로서비스인가요?**  
A. 아니요. 단일 FastAPI 앱 + (선택) 외부 SaaS(Clerk/Neon/LLM).

**Q. AI 서비스인가요?**  
A. **AI 보조 검수 도구**입니다. 핵심 판정은 규칙 엔진이고 AI는 설명 레이어입니다.

**Q. 컬럼명이 한글이면요?**  
A. 별칭 레이어가 정규 키로 바꾼 뒤 동일 10룰을 적용하고, `column_mappings`로 기록합니다.

**Q. 로그인을 안 하면?**  
A. 검수·리포트는 됩니다. 이력 대시보드만 막힙니다.

**Q. 새 검수 항목을 넣으려면?**  
A. 룰 파일 하나 + 레지스트리 한 줄. 스키마·프롬프트 재학습 불필요.

**Q. 장애 시나리오?**  
A. LLM 다운 → fallback 서술. DB 다운 → 인메모리/저장 스킵, 검수 200. Clerk 이슈 → 검수는 유지, 대시보드만 영향.

---

## 12. 30초 / 2분 / 5분 버전

| 길이 | 말할 것 |
|------|---------|
| **30초** | 등록 전 3파일 검수. 판정은 룰, 설명은 AI. 같은 입력 같은 결과. |
| **2분** | 위 + 두 경로(판정/이력) + 별칭 + 비로그인 검수 + 데모 한 컷 |
| **5분** | 위 + Context/Issue/Report + 룰 확장 비용 + D3 이유 + degrade 전략 |

---

*관련 심화 문서*: `BACKEND_ARCHITECTURE.md` · `README.md` · `docs/rule-matrix.md` · `docs/dev-journal-2026-07-14-to-0723.md`
