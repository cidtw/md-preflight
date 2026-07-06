---
version: alpha
name: MD-Preflight-design-system
description: >
  MD Preflight의 MVP 웹 UI를 위한 디자인 시스템. 유통 프로모션 사전검수라는
  B2B 운영·감사 도메인에 맞춰 Vercel의 near-white ink-on-white 팔레트와
  Linear의 조밀한 hairline·surface 위계를 합성하고, 이슈 심각도(error/warning)는
  Sentry식 시맨틱 색 코딩으로 구분한다. 화면은 "파일 3개 업로드 → 결정론적
  이슈 목록 → AI 요약·체크리스트 → Markdown 리포트"의 검수 흐름을 그대로 반영한다.
  핵심 정서는 밝고 조밀하고 군더더기 없는 신뢰감 — 판정은 규칙 엔진이,
  서술만 LLM이 한다는 제품 원칙을 UI가 시각적으로 증명한다.

# ─────────────────────────────────────────────
# COLORS  (light canvas · ink-on-white · single blue accent · severity semantics)
# ─────────────────────────────────────────────
colors:
  # Brand / accent — 파랑 하나만 크로매틱 액센트로 쓴다 (Vercel 규율)
  primary: "#0070f3"
  on-primary: "#ffffff"
  primary-hover: "#0761d1"
  primary-soft: "#d3e5ff"

  # Ink (text)
  ink: "#171717"          # 헤드라인·강조 본문
  body: "#4d4d4d"         # 기본 본문
  mute: "#888888"         # 보조·메타·placeholder
  faint: "#a1a1a1"        # 비활성·각주

  # Surface (canvas 위 3단 위계 — 그림자 대신 톤 차이로 깊이)
  canvas: "#ffffff"       # 페이지 기본 배경
  surface-1: "#fafafa"    # 카드·패널
  surface-2: "#f5f5f5"    # 중첩 패널·테이블 헤더·hover
  overlay-scrim: "rgba(0,0,0,0.4)"

  # Hairline (1px 경계 — 이 시스템의 주된 구분 장치)
  hairline: "#ebebeb"
  hairline-strong: "#a1a1a1"

  # ── Severity semantics (이슈 심각도 코딩 — 이 제품의 심장) ──
  # error : 등록을 막아야 하는 치명 이슈 (INVALID_DATE_RANGE 등)
  severity-error: "#ee0000"
  severity-error-soft: "#f7d4d6"   # 배지·행 배경 tint
  severity-error-deep: "#c50000"   # 텍스트·아이콘
  # warning : 확인 후 진행 가능한 리스크 (EXTREME_DISCOUNT_RATE 등)
  severity-warning: "#f5a623"
  severity-warning-soft: "#ffefcf"
  severity-warning-deep: "#ab570a"
  # info : 참고 메타 (dedup 안내 등)
  severity-info: "#0070f3"
  severity-info-soft: "#d3e5ff"
  severity-info-deep: "#0761d1"
  # pass / ok : 통과 검수·clean 상태
  severity-ok: "#0a7d33"
  severity-ok-soft: "#d6f0dd"
  severity-ok-deep: "#075c26"

  # Provenance badge (generated_by — 제품 신뢰성의 핵심 시그널)
  provenance-llm: "#7928ca"        # LLM 서술 경로
  provenance-fallback: "#888888"   # 결정론적 fallback 서술 경로

  # Code / mono surfaces
  code-bg: "#f5f5f5"
  code-ink: "#171717"
  selection-bg: "#171717"
  selection-fg: "#f2f2f2"

# ─────────────────────────────────────────────
# TYPOGRAPHY  (Geist/Inter 계열 · 음수 트래킹 · 데이터엔 mono)
# ─────────────────────────────────────────────
typography:
  display-lg:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 32px
    fontWeight: 600
    lineHeight: 40px
    letterSpacing: -1.28px      # 헤로/페이지 타이틀. 프로덕트 툴이라 40px+는 지양
  display-md:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 24px
    fontWeight: 600
    lineHeight: 32px
    letterSpacing: -0.96px      # 섹션 제목 ("검수 결과", "담당자 체크리스트")
  display-sm:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 20px
    fontWeight: 600
    lineHeight: 28px
    letterSpacing: -0.6px       # 카드 타이틀, 이슈 그룹 헤더
  body-lg:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0px          # 리드 문장, AI 요약 본문
  body:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px            # 기본 본문
  body-strong:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 500
    lineHeight: 24px
  body-sm:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: -0.28px      # 테이블 셀, 카드 보조 텍스트
  body-sm-strong:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
    letterSpacing: -0.28px      # 테이블 헤더, 라벨
  caption:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px            # 메타, 파일명 하단 정보, 타임스탬프
  eyebrow:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 12px
    fontWeight: 500
    lineHeight: 16px
    letterSpacing: 0.4px        # 섹션 위 소제목 (양수 트래킹 = 분류 신호)
  mono:
    fontFamily: Geist Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px            # 룰 코드, 상품코드, 셀 값, 숫자 데이터
  mono-sm:
    fontFamily: Geist Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px            # 배지 안 룰 코드
  button:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px

# ─────────────────────────────────────────────
# SHAPES
# ─────────────────────────────────────────────
rounded:
  none: 0px
  xs: 4px      # 배지, 칩
  sm: 6px      # 버튼, 인풋
  md: 8px      # 카드, 드롭존
  lg: 12px     # 큰 패널, 리포트 프리뷰
  pill: 9999px # 상태 pill, 토글

# ─────────────────────────────────────────────
# SPACING  (4px base — Linear식 조밀 리듬)
# ─────────────────────────────────────────────
spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 64px    # 프로덕트 툴이라 마케팅용 96px+ 리듬은 쓰지 않는다

# ─────────────────────────────────────────────
# COMPONENTS  (md-preflight의 실제 화면 표면에 1:1로 매핑)
# ─────────────────────────────────────────────
components:
  # ── App shell ──
  top-nav:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    borderColor: "{colors.hairline}"    # 하단 1px hairline
    height: 56px
    padding: "0px {spacing.lg}"

  # ── Buttons ──
  button-primary:                        # "검수 실행", "리포트 다운로드"
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.md}"
    height: 36px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:                      # "다시 업로드", "취소"
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline-strong}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.md}"
    height: 36px
  button-ghost:                          # 인라인 액션 ("셀 보기", "복사")
    backgroundColor: "transparent"
    textColor: "{colors.body}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.sm}"
    height: 28px

  # ── File upload (MVP 진입 화면: 파일 3개 = promotion_plan / product_master / inventory) ──
  file-dropzone:                         # 기본 상태
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.mute}"
    borderColor: "{colors.hairline-strong}"   # 1px dashed
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.xl}"
  file-dropzone-dragover:                # 파일을 끌어다 놓는 중
    backgroundColor: "{colors.primary-soft}"
    borderColor: "{colors.primary}"
  file-dropzone-filled:                  # 파일이 올라간 상태
    backgroundColor: "{colors.canvas}"
    borderColor: "{colors.severity-ok}"       # 1px solid, 파일명·크기 표시
    textColor: "{colors.ink}"
  file-dropzone-error:                   # 잘못된 형식·파싱 실패
    backgroundColor: "{colors.severity-error-soft}"
    borderColor: "{colors.severity-error}"
    textColor: "{colors.severity-error-deep}"

  # ── Verdict banner (검수 결과 최상단: PASS / FAIL 판정) ──
  verdict-banner-pass:
    backgroundColor: "{colors.severity-ok-soft}"
    textColor: "{colors.severity-ok-deep}"
    borderColor: "{colors.severity-ok}"       # 좌측 3px accent bar
    typography: "{typography.display-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.md} {spacing.lg}"
  verdict-banner-fail:
    backgroundColor: "{colors.severity-error-soft}"
    textColor: "{colors.severity-error-deep}"
    borderColor: "{colors.severity-error}"
    typography: "{typography.display-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.md} {spacing.lg}"

  # ── Stat tile (요약 카운트: error N · warning N · 검수 상품 N) ──
  stat-tile:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.display-md}"     # 큰 숫자
    rounded: "{rounded.md}"
    padding: "{spacing.md} {spacing.lg}"
    # label 은 caption + mute, 값은 display-md + ink

  # ── Issue list (이 제품의 protagonist — Sentry식 severity 행) ──
  issue-row:                             # 리스트 한 줄
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"          # 하단 1px 구분선
    typography: "{typography.body-sm}"
    rounded: "{rounded.none}"
    padding: "{spacing.md} {spacing.lg}"
    # 좌측 3px severity accent bar (error=red / warning=amber / info=blue)
  issue-row-hover:
    backgroundColor: "{colors.surface-1}"
  issue-card:                            # 확장/모바일 카드형
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"

  # ── Badges ──
  severity-badge-error:
    backgroundColor: "{colors.severity-error-soft}"
    textColor: "{colors.severity-error-deep}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.xs}"
    padding: "2px {spacing.xs}"
  severity-badge-warning:
    backgroundColor: "{colors.severity-warning-soft}"
    textColor: "{colors.severity-warning-deep}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.xs}"
    padding: "2px {spacing.xs}"
  severity-badge-info:
    backgroundColor: "{colors.severity-info-soft}"
    textColor: "{colors.severity-info-deep}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.xs}"
    padding: "2px {spacing.xs}"
  rule-code-chip:                        # INVALID_DATE_RANGE 등 — 항상 mono
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.body}"
    typography: "{typography.mono-sm}"
    rounded: "{rounded.xs}"
    padding: "2px {spacing.xs}"
  provenance-badge-llm:                  # generated_by=llm
    backgroundColor: "transparent"
    textColor: "{colors.provenance-llm}"
    borderColor: "{colors.provenance-llm}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.pill}"
    padding: "2px {spacing.xs}"
  provenance-badge-fallback:             # generated_by=fallback
    backgroundColor: "transparent"
    textColor: "{colors.provenance-fallback}"
    borderColor: "{colors.hairline-strong}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.pill}"
    padding: "2px {spacing.xs}"

  # ── AI summary panel (LLM 서술 — 판정선 밖의 "사람 말") ──
  ai-summary-panel:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.body}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-lg}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
    # 우상단에 provenance-badge 를 반드시 노출

  # ── Checklist (담당자 실행 체크리스트) ──
  checklist-item:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "{spacing.sm} 0px"

  # ── Data table (joined 뷰 · 이슈 상세 셀 값) ──
  data-table-header:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.body}"
    typography: "{typography.body-sm-strong}"
    borderColor: "{colors.hairline}"
    padding: "{spacing.xs} {spacing.sm}"
  data-table-cell:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    borderColor: "{colors.hairline}"
    padding: "{spacing.xs} {spacing.sm}"
  data-table-cell-numeric:               # 가격·마진·수량 — mono + 우측 정렬
    typography: "{typography.mono}"

  # ── Report preview / actions (Markdown·PDF) ──
  report-preview:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  code-block:                            # raw Markdown 미리보기
    backgroundColor: "{colors.code-bg}"
    textColor: "{colors.code-ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"

  # ── States ──
  empty-state-clean:                     # 이슈 0건 (clean 검수)
    backgroundColor: "{colors.severity-ok-soft}"
    textColor: "{colors.severity-ok-deep}"
    typography: "{typography.body-lg}"
    rounded: "{rounded.md}"
    padding: "{spacing.xl}"
  toast-error:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.md}"
---

## Overview

MD Preflight의 UI는 **검수 도구**다. 마케팅 캔버스가 아니라, 담당자(MD)가
등록 버튼을 누르기 전에 리스크를 한눈에 확인하는 **밀도 높은 운영 화면**이다.
따라서 이 시스템은 화려함을 버리고 **명료함·조밀함·신뢰감**을 택한다.

- **Canvas**: `{colors.canvas}` 순백. 그 위에 `{colors.surface-1}`(#fafafa),
  `{colors.surface-2}`(#f5f5f5) 3단 톤으로 위계를 만든다. **그림자는 거의 쓰지 않는다** —
  깊이는 1px `{colors.hairline}` 경계와 surface 톤 차이가 만든다 (Linear의 규율을 라이트로 이식).
- **Accent**: 파랑 `{colors.primary}`(#0070f3) 하나만 크로매틱 액센트로 쓴다.
  주 CTA·링크·포커스 링·info 시맨틱에만. 장식용으로 파랑을 뿌리지 않는다 (Vercel의 규율).
- **Severity가 유일한 다색 예외**: error(빨강)·warning(주황)·ok(초록)은 **의미를 가진 색**이라
  액센트 규율의 예외다. 이 색들은 오직 이슈 심각도·판정 상태에만 쓴다 (Sentry식 시맨틱 코딩).
- **Typography**: Geist(대체: Inter) 한 계열로 display→body를 잇고, 음수 트래킹을
  display에 적극 준다. **데이터는 전부 mono**(Geist Mono) — 룰 코드·상품코드·가격·마진·수량.
- **Rhythm**: 4px base, `{spacing.section}` 64px. 프로덕트 툴이라 마케팅용 96px+ 여백은 쓰지 않는다.

**핵심 성격**
- 밝은 near-white 시스템 — `#000000` 순검정 캔버스는 쓰지 않는다.
- 파랑 단일 액센트 + 의미 기반 severity 3색(error/warning/ok)만 예외.
- 깊이는 hairline + surface 톤 (그림자 아님).
- 데이터·코드는 mono, 문장은 sans — 이 대비가 "판정(데이터) vs 서술(문장)"을 시각화한다.
- 이슈 목록이 protagonist. 나머지 크롬은 이슈가 주인공이 되게 비운다.

## 제품 원칙이 UI로 번역되는 방식

MD Preflight의 제품 철학은 **"판정은 결정론적 규칙 엔진이, 서술만 LLM이 한다"**이다.
UI는 이 경계를 **시각적으로 증명**해야 한다.

| 제품 개념 | UI 표현 |
|---|---|
| 결정론적 판정 (rule engine) | 이슈 목록·룰 코드·판정 배너 — **mono·확정적·색으로 심각도 고정** |
| LLM 서술 (요약·체크리스트) | `ai-summary-panel` — sans 본문, **provenance 배지로 출처 표기** |
| `generated_by = llm / fallback` | `provenance-badge-llm`(보라) / `provenance-badge-fallback`(회색) — **항상 노출** |
| "데모는 안 죽는다" (fallback) | fallback 서사도 동일한 레이아웃으로 렌더 — 다운 상태를 만들지 않는다 |

**규칙**: AI가 쓴 문장(요약·체크리스트)은 반드시 provenance 배지를 달아
"이건 서술이지 판정이 아니다"를 알린다. 판정 데이터(이슈·룰 코드·카운트)에는 배지를 달지 않는다.

## Colors

### Accent & Ink
- **Primary Blue** (`{colors.primary}` #0070f3): 주 CTA, 링크, 포커스 링, info 시맨틱. 이것 하나뿐.
- **Ink** (`{colors.ink}` #171717): 헤드라인·강조. **Body** (#4d4d4d): 본문. **Mute** (#888888): 메타·placeholder.

### Surface & Hairline
- **Canvas → surface-1 → surface-2**: 톤 3단으로 위계. 카드는 surface-1, 테이블 헤더·hover는 surface-2.
- **Hairline** (#ebebeb): 거의 모든 경계. **Hairline-strong** (#a1a1a1): 인풋 테두리·dashed 드롭존.

### Severity (의미 기반 — 이 색들은 심각도에만)
| 시맨틱 | solid | soft(배경 tint) | deep(텍스트) | 매핑되는 룰 예 |
|---|---|---|---|---|
| **error** | #ee0000 | #f7d4d6 | #c50000 | `INVALID_DATE_RANGE`, `INVALID_PROMO_PRICE`, `MISSING_PRODUCT_MASTER` |
| **warning** | #f5a623 | #ffefcf | #ab570a | `EXTREME_DISCOUNT_RATE`, `INVENTORY_SHORTAGE_RISK`, `INBOUND_DATE_CONFLICT` |
| **info** | #0070f3 | #d3e5ff | #0761d1 | dedup 안내 등 참고 메타 |
| **ok** | #0a7d33 | #d6f0dd | #075c26 | 이슈 0건 clean 상태, 채워진 드롭존 |

> `LOW_MARGIN_RATE`처럼 **warning→error 승격** 룰은, 승격 시 warning이 아니라 error 색으로 렌더한다.
> severity 값(`app/schemas/issue.py`의 최종 판정)을 그대로 색에 매핑할 것 — UI가 임의로 재판정하지 않는다.

### Provenance
- **LLM** (#7928ca 보라 아웃라인 pill): LLM이 서술을 생성한 경로.
- **Fallback** (#888888 회색 아웃라인 pill): 결정론적 fallback 서사 경로.

## Typography

| Token | Size / Weight | 용도 |
|---|---|---|
| `{typography.display-lg}` | 32 / 600, -1.28px | 페이지 타이틀 ("MD Preflight") |
| `{typography.display-md}` | 24 / 600, -0.96px | 섹션 제목, stat-tile 숫자 |
| `{typography.display-sm}` | 20 / 600, -0.6px | 카드·판정 배너·이슈 그룹 헤더 |
| `{typography.body-lg}` | 18 / 400 | AI 요약 본문, 리드 문장 |
| `{typography.body}` | 16 / 400 | 기본 본문, 체크리스트 |
| `{typography.body-sm}` | 14 / 400, -0.28px | 테이블 셀, 이슈 행, 카드 보조 |
| `{typography.caption}` | 12 / 400 | 메타, 파일 크기, 타임스탬프 |
| `{typography.eyebrow}` | 12 / 500, +0.4px | 섹션 소제목, 배지 라벨 (양수 트래킹) |
| `{typography.mono}` | 13 / 400 mono | **룰 코드·상품코드·가격·마진·수량** |

**원칙**
- display에 음수 트래킹을 적극 준다. eyebrow만 양수 트래킹(분류 신호).
- **데이터는 전부 mono.** 상품코드·행사가·마진율·수량·룰 코드는 절대 sans로 쓰지 않는다 —
  숫자 자릿수 정렬과 "기계가 판정한 값"이라는 시각 신호를 위해.
- 문장(요약·체크리스트·설명)은 sans. **mono=판정, sans=서술**의 대비를 지킨다.
- 폰트 미보유 시: Geist → **Inter** 500/600, Geist Mono → **JetBrains Mono** / IBM Plex Mono.

## Layout

- **Base unit** 4px. Container max ~1120px (데이터 밀도가 높아 마케팅용 1280px보다 좁게).
- **업로드 화면**: 3개 `file-dropzone`를 3-up(데스크톱) → 1-up(모바일). 각 존에 파일 역할 라벨
  (promotion_plan / product_master / inventory)을 eyebrow로 고정.
- **결과 화면 순서**(위→아래): `verdict-banner` → `stat-tile` 행 → 이슈 목록 →
  `ai-summary-panel` → 체크리스트 → 리포트 액션. 검수 흐름과 동일한 세로 읽기.
- **여백 철학**: 섹션은 `{spacing.section}` 64px, 카드 내부는 `{spacing.lg}` 24px,
  조밀한 리스트/테이블은 `{spacing.sm}` 12px. 흰 여백보다 **hairline으로 구분**한다.

## Elevation & Depth

| Level | 처리 | 용도 |
|---|---|---|
| 0 (flat) | 배경·경계 없음 | 본문, 헤로 텍스트 |
| 1 (surface lift) | `{colors.surface-1}` + 1px `{colors.hairline}` | 카드, 패널, 드롭존 |
| 2 (tone lift) | `{colors.surface-2}` | 테이블 헤더, hover, 중첩 패널 |
| 3 (accent bar) | 좌측 3px severity/verdict 컬러 바 | 이슈 행, 판정 배너 |
| 4 (focus ring) | 2px `{colors.primary}` 아웃라인 (50% opacity) | 포커스된 인풋·버튼 |

깊이는 hairline + 톤 + accent bar가 만든다. **드롭 섀도는 토스트·모달 등 진짜 뜬 표면에만** 아주 옅게.

## Components

### 이슈 목록 (protagonist)
`issue-row`는 좌측 **3px severity accent bar** + `severity-badge` + `rule-code-chip`(mono) +
사람이 읽는 메시지 + 영향 행/상품코드(mono, 우측)로 구성한다. 정렬 기본값은 **severity desc**
(error 먼저), 동일 severity 내에서는 룰 코드 알파벳순. hover 시 `{colors.surface-1}`로 lift.

### 판정 배너
`verdict-banner-pass`(초록) / `verdict-banner-fail`(빨강)를 결과 화면 최상단에 둔다.
문구는 확정적으로: "검수 통과 — 이슈 없음" / "검수 실패 — error N건, warning N건".

### Stat tiles
error 수 · warning 수 · 검수 상품 수를 `stat-tile` 3~4개로. 큰 숫자는 `display-md`,
error 카운트가 1 이상이면 숫자를 `{colors.severity-error-deep}`로 물들인다.

### AI 요약 & Provenance
`ai-summary-panel` 우상단에 `provenance-badge`를 **항상** 표기. LLM이면 보라, fallback이면 회색.
이것이 제품 신뢰성의 핵심 UI다 — 사용자는 이 서술이 어느 경로인지 항상 알 수 있어야 한다.

### 데이터 테이블
셀 값·상품코드·가격·마진은 `data-table-cell-numeric`(mono, 우측 정렬). 헤더는 surface-2.
zebra stripe 대신 hairline row 구분.

## Do's and Don'ts

### Do
- 파랑 `{colors.primary}`은 CTA·링크·포커스·info에만. severity 3색은 심각도에만.
- 모든 숫자·코드·룰명은 mono. 모든 문장은 sans.
- 이슈 행에 좌측 3px severity bar를 붙여 스캔 가능성을 높인다.
- AI 서술에는 provenance 배지를 반드시 단다.
- 깊이는 hairline + surface 톤으로. 그림자는 아낀다.
- severity는 백엔드가 확정한 값을 그대로 색에 매핑한다.

### Don't
- 파랑을 카드 배경·섹션 배경으로 칠하지 않는다.
- error/warning 색을 장식·강조용으로 전용하지 않는다 (의미 오염).
- 판정 데이터(이슈·카운트)에 provenance 배지를 달지 않는다 (그건 사실이지 서술이 아니다).
- UI에서 severity를 재계산·재판정하지 않는다.
- 마케팅용 대형 헤로·아트무스피어 그라디언트·스포트라이트 카드를 넣지 않는다.
- `#000000` 순검정 캔버스, pill CTA 남용 금지.

## Responsive Behavior

| Breakpoint | Width | 변화 |
|---|---|---|
| Desktop | ≥1024px | 드롭존 3-up, stat-tile 4-up, 이슈=테이블 행 |
| Tablet | 768–1023px | 드롭존 3-up 유지, stat-tile 2-up |
| Mobile | <768px | 드롭존 1-up, stat-tile 2-up, **이슈 행 → `issue-card`로 전환**, 테이블 가로 스크롤 |

- 터치 타깃 ≥44px. 데이터 테이블은 모바일에서 가로 스크롤 컨테이너 안에 가둔다(본문은 가로 스크롤 금지).

## 이 파일을 쓰는 법 (Vercel MVP 빌드)

1. 이 `DESIGN.md`를 프로젝트 루트에 둔 채로 AI 코딩 에이전트에게
   "DESIGN.md의 토큰·컴포넌트를 따라 업로드 화면 / 결과 화면을 만들어줘"라고 지시한다.
2. 컴포넌트는 `components:`의 토큰 이름으로 지목한다 (예: "`issue-row`를 만들어줘").
3. 색·타이포·간격은 하드코딩하지 말고 위 토큰을 CSS 변수(`--severity-error` 등)로 뽑아 쓴다.
4. 백엔드 계약(`app/schemas/report.py`의 `PreflightReport`)의
   `issues[].severity`, `summary`, `generated_by`를 UI 토큰에 그대로 매핑한다.
5. 새 변형이 필요하면 별도 component 엔트리로 추가한다 (기존 토큰을 오염시키지 않는다).

## Sources & References

이 시스템은 `projects/../awesome-design-md/design-md` 컬렉션에서 합성했다:
- **Vercel** — near-white ink-on-white 팔레트, 파랑 단일 액센트, 시맨틱 색(error/warning), Geist 타이포.
- **Linear** — 조밀한 hairline·surface 위계, 음수 트래킹, "그림자 대신 톤" 깊이, 프로덕트 밀도.
- **Sentry** — 이슈·심각도 중심 리스트 UI 패턴 (severity 색 코딩·좌측 accent bar).
- 참고용 원본 브랜드 DESIGN.md는 `docs/design-references/`에 사본으로 두었다.

원본 컬렉션: <https://github.com/VoltAgent/awesome-design-md> · DESIGN.md 개념: Google Stitch.
