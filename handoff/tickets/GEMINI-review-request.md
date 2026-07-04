# Gemini 검토 요청서 (md-preflight)

## 역할
너(Gemini)는 이 프로젝트의 **대용량 대조 감사자 + 적대적 리뷰어**다. 구현은 하지 마라. 아래 4개 항목을 검토하고, 발견을 **증거(파일·라인)와 함께** 보고하라. 정본 레포는 `projects/md-preflight`.

## 프로젝트 한 줄 요약
유통 프로모션 사전 검수 도구. 설계원칙: **판단은 deterministic rule engine, 서술만 LLM.** LLM은 판정에 절대 개입하지 않는다. 취업용 포트폴리오 프로젝트라 설계 의도·테스트 가능성·문서 품질이 코드만큼 중요하다.

## 먼저 읽을 것
- `PROJECT_BRIEF.md`, `BACKEND_ARCHITECTURE.md` (설계 계약)
- `app/rules/*.py` (8개 룰), `app/rules/__init__.py`(RULES 레지스트리), `app/rules/base.py`
- `app/domain/context.py`, `app/domain/columns.py`, `app/ingest/normalize.py`
- `app/core/rule_config.py` (임계값), `app/services/validation_engine.py`, `app/services/llm_service.py`
- `tests/test_rules.py`, `tests/conftest.py`

## 검토 항목

### G-1. 문서 ↔ 코드 정합성 전수 대조
`BACKEND_ARCHITECTURE.md §3.2`의 8개 룰 판정 로직표(판정식·severity·임계값·severity 승격 조건)와 `app/rules/*.py` 실제 구현을 **룰 단위로 1:1 대조**하라.
- 각 룰: 문서의 판정식 == 코드의 마스크 조건인가? severity 값 일치? 임계값이 `RuleThresholds`(`max_discount_rate=0.7`, `min_margin_rate=0.05`)와 일치?
- 특히 `margin_rate`의 "마진 음수면 error 승격" 로직이 문서와 코드에서 동일 기준인지.
- 출력: 룰별 `일치/불일치(무엇이)` 표.

### G-2. LLM 경계 안전성 (설계 관점 — 현재는 fallback만 구현됨)
현 `llm_service.py`는 fallback 템플릿뿐이고 실제 LLM 호출은 후속 티켓 T6에서 붙는다. **T6 구현 전에** 다음을 적대적으로 검토하라.
- 설계원칙("LLM이 판정을 못 만들게")을 실제로 강제하려면 프롬프트/스키마에 어떤 제약이 반드시 있어야 하는가?
- LLM이 이슈를 새로 만들거나 개수/severity를 바꾸는 우회 경로가 생길 수 있는 지점은 어디인가?
- 이를 막는 **계약 테스트(T8)**가 실제로 무엇을 assert 해야 결정론 불변을 증명하는가? 구체적 테스트 케이스를 제안하라.

### G-3. 룰 커버리지 공백
`tests/test_rules.py`가 8개 룰의 실패 모드를 충분히 덮는지 감사하라. 놓쳤을 법한 엣지:
- `promo_price == 0` / 음수, 날짜 파싱 실패(`NaT`), `normal_price`/`cost` 결측(NaN),
- product_master 조인 다중 매칭(중복 product_code), inventory 결측 행,
- `benefit_type`은 있는데 `benefit_condition` 공백 vs 둘 다 공백.
- 출력: `룰 × 놓친 엣지케이스` 목록 + 각 케이스가 왜 위험한지 한 줄.

### G-4. 포트폴리오 냉정 평가 (채용 리뷰어 시선)
- 이 프로젝트가 "유통 도메인 이해 + 엔지니어링 역량"을 동시에 증명하는가? 가장 약한 고리는?
- 시니어 리뷰어가 5분 훑었을 때 감점 요인 3가지와 가점 요인 3가지.
- README(작성 예정)에 반드시 들어가야 할, 지금 코드가 이미 증명하는 강점은?

## 출력 형식
항목별로 (1) 발견 요약 (2) 증거 `파일:라인` (3) 심각도(높음/중간/낮음) (4) 권장 조치. 코드 수정 금지 — 진단·제안만.

## 하지 말 것
- 코드 구현/수정 금지. 아키텍처를 새로 갈아엎는 제안 금지(3주 MVP 스코프 존중: ERP/POS/로그인/수요예측 제외는 의도된 것).
- 추상적 조언 금지. 이 repo의 실제 파일·라인에 근거한 지적만.
