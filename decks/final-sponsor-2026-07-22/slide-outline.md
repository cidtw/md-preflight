# 매장 특화 발주 기준 재조정 — 최종 발표 (주관기관용)

> **slides-grab Stage 1 (Plan)**  
> 근거: `last_week_plan.md` (7/22 14:00, 6분, 경기도기술학교 북부캠퍼스 팀장, 7/24 개소식 후보)  
> 기존 14장 기술 덱(`projects/md-preflight/slides/`)은 **보관용**. 본 덱이 **당일 발표 정본**.

## Meta
- **Topic**: 매장 특화 ROP 재조정 서비스 — 목적·기능·효과 + 기술 흐름 + 시연 영상
- **Target Audience**: 프로젝트 주관기관 담당자 (경기도기술학교 북부캠퍼스 팀장) · 교육·공공 맥락 · 비개발자 중심 (기술 장은 한 장만, 쉬운 말)
- **Tone/Mood**: 간단명료 · 신뢰 · 공공/교육 기관 발표에 맞는 절제된 공식감 · 전문 용어 최소화
- **Slide Count**: **8 slides** (6분; 기술 1장·영상 1장 포함)
- **Aspect Ratio**: 16:9
- **Style**: `warm-neutral` (웜 뉴트럴 · 후보 C 사용자 선택 2026-07-21; 이전 A 폐기)
- **Language**: 한국어 구어체. ROP/LT/SS 등은 **쓰지 않거나 한 번만 풀어 씀**. 기술 장표만 스택 이름 병기.
- **Live**: https://baljumatch.vercel.app
- **Branch**: `pivot/project-direction` (main = v1 아카이브)
- **Demo asset**: `assets/demo-walkthrough.mp4` (**~36s trim** from user `2026-07-21 09-29-23.mov`: 1–13.5s + 28.5–52s) · poster `assets/demo-poster.png`
- **Not in this deck**: pytest KPI 차트, L1–L3 문헌 매트릭스, CAPA 수식 전개, git 브랜치 서사, v1 Clerk/Neon/LLM 스택
- **Status**: **Stage 2 candidate ready (2026-07-21)** — style **warm-neutral (C)** · 8 HTML · validate · design-gate Proceed · PDF

## Narrative Arc (한 줄)

```
무엇이냐 → 왜 → 어떻게 쓰냐 → 기능 → 기술 흐름 → 효과 → 시연 영상 → 한 줄 요약
```

## Speaking budget (6분)

| 구간 | 시간 | 슬라이드 |
|------|------|----------|
| 오프닝·한 줄 정의 | ~45s | 1–2 |
| 문제·목적 | ~50s | 3 |
| 사용·기능 | ~70s | 4–5 |
| 기술 스택 흐름 | ~45s | 6 |
| 효과 | ~35s | 7 |
| 시연 영상 재생 + 클로징 | ~55s | 8 (영상 ~36s · 멘트 최소) |
| **합계** | **~6분** | |

## Slide Composition

### Slide 1 - Cover
- **Type**: Cover
- **Title**: 매장마다 다른 발주 기준, 한 번에 맞춥니다
- **Subtitle**: 매장·상권 정보로 안전재고와 발주 시점을 제안하는 재고 운영 도구
- **Kicker**: 2026.07.22 · 최종 발표 · 경기도기술학교 북부캠퍼스
- **Chips**: 목적 · 기능 · 효과 | 기술 한 장 | 시연 영상
- **Presenter**: 권태원 · 발주맞춤 · OrderFit
- **Notes**: 인사 후 제목 한 번만 읽고 바로 2장.

### Slide 2 - 한 장으로 보는 프로젝트
- **Type**: Content / Three-column
- **Key Message**: 이 프로젝트는 “매장 맞춤 발주 도우미”입니다.
- **Details**:
  - **제목(무엇인지)**: 매장 특화 발주 기준 재조정 서비스
  - **목적**: 같은 업계 평균 기준이 아니라, **이 매장**에 맞는 발주 시점을 제안
  - **한 줄 결과**: 입력 → 자동 계산 → “언제·얼마나 발주할지” 리포트
- **Visual**: 3칸 카드 (무엇인지 / 왜 / 결과 한 줄)
- **Notes**: 슬라이드에는 **발주 시점** 표기. ROP는 구두 선택.

### Slide 3 - 왜 필요한가 (문제 → 목적)
- **Type**: Content / Two-column
- **Key Message**: 평균 기준으로 시키면, 어떤 매장은 품절·어떤 매장은 재고 과잉이 납니다.
- **Details**:
  - **문제**: 매장마다 조건이 다른데 발주 기준은 한 가지 표준 · “왜 이 숫자인지” 설명 어려움
  - **목적**: 매장 정보만 넣으면 **맞춤 발주 기준 + 근거** · 현장 담당자가 이해·적용 가능
- **Visual**: 좌 문제 · 우 목적(네이비 강조)
- **Notes**: v1 피벗 서사 생략.

### Slide 4 - 어떻게 쓰나요 (3단계)
- **Type**: Content / Process
- **Key Message**: 세 단계뿐입니다. 입력 → 분석 → 제안.
- **Details**:
  1. **입력** — 매장 유형·규모·위치·상권·하루 판매량
  2. **분석** — 같은 입력 → 같은 결과 · 근거 표시
  3. **제안** — 발주 시점 · 안전재고 · 1회 발주량 · 표준과 비교
- **Visual**: 가로 3단 플로우
- **Notes**: 제안이지 자동 발주 결정이 아님.

### Slide 5 - 주요 기능
- **Type**: Content / Feature cards (4)
- **Key Message**: 쓰기 쉽고, 결과가 분명하고, 근거가 남습니다.
- **Details**:
  1. **따라 하기 쉬운 입력** — 질문형 화면
  2. **맞춤 발주 제안** — 매장 기준 vs 표준 비교
  3. **왜 이 숫자인가** — 근거 문장
  4. **결과 가져가기** — 리포트 저장·공유
- **Visual**: 2×2 카드

### Slide 6 - 기술 스택과 데이터 흐름  ← NEW
- **Type**: Content / Architecture flow (비전공 친화)
- **Key Message**: 화면 → 서버 → 계산 → 결과. 쓰는 기술이 한 줄로 이어집니다.
- **Details — 스택 목록 (역할 한 줄씩)**:

  | 구분 | 기술 | 이 프로젝트에서의 역할 |
  |------|------|------------------------|
  | 화면 | HTML · CSS · JavaScript | 입력 위저드 · 결과 리포트 UI |
  | 서버 API | FastAPI (Python) | 요청 받기 · `/api/evaluate` 등 |
  | 입력 검증 | Pydantic | 잘못된 값 걸러 내기 |
  | 계산 엔진 | Python 파이프라인 3단 | 입력 → 분석 → 출력 (같은 입력 = 같은 결과) |
  | 위치 보조 (선택) | Kakao Local API | 주소·주변 점포 보조 (키 없으면 저장본 사용) |
  | 배포 | Vercel | 인터넷에서 바로 접속 가능한 서비스 |
  | 품질 확인 | pytest · ruff | 자동 검사로 결과 안정성 유지 |

- **Details — 흐름 (슬라이드 본문 다이어그램)**:
  ```
  [브라우저 화면]
        │  사용자가 매장 정보 입력 / 시연 카드 선택
        ▼
  [FastAPI 서버]  ←── Vercel에 올려 둠
        │  Pydantic으로 입력 확인
        ▼
  [파이프라인]  입력 정리 → 점수·지식 매칭 → 발주 기준 계산
        │
        ▼
  [JSON 결과] → 화면에 쉬운 설명 · 근거 · 비교 리포트
  ```
- **Visual**: 상단 가로 플로우 5박스 + 하단 스택 칩(역할 짧은 라벨). 코드 스니펫·로고 나열 금지.
- **Notes (발표 멘트 예시)**:
  - “화면은 웹, 계산은 파이썬 서버가 합니다.”
  - “같은 값을 넣으면 같은 답이 나오도록 계산 규칙을 고정했습니다.”
  - “지도·주소는 카카오를 쓸 수 있고, 없어도 시연은 됩니다.”
  - v1의 Clerk·DB·LLM은 **현재 제품 스택이 아님** — 말하지 않음.

### Slide 7 - 기대 효과
- **Type**: Content / Three outcomes
- **Key Message**: 현장 판단이 빨라지고, 설명이 가능해집니다.
- **Details**:
  - **빠른 의사결정** — 한 화면에서 기준 확인
  - **설명 가능한 숫자** — “왜 이 발주량인가”
  - **매장 맞춤** — 평균이 아닌 이 점포 조건
- **Visual**: 3 outcome 카드
- **Notes**: 검증 안 된 % 절감 수치 금지.

### Slide 8 - 시연 영상 · 마무리  ← UPDATED (video)
- **Type**: Closing / Demo video
- **Key Message**: 실제로 이렇게 돌아갑니다. (약 36초)
- **Details**:
  - **영상**: `./assets/demo-walkthrough.mp4`
    - 원본: `~/Downloads/2026-07-21 09-29-23.mov` (~62.7s)
    - **트리밍**: 1.0–13.5s (홈·매장 선택) + 28.5–52.0s (결과 리포트) → **~36s** · 로딩 구간 제거
  - **poster**: `./assets/demo-poster.png` (PDF export용 정지 화면)
  - **URL**: https://baljumatch.vercel.app (현장에서 다시 열 수 있음)
  - **한 줄 요약**: *매장 정보를 넣으면, 그 매장에 맞는 발주 기준과 이유를 제안합니다.*
  - **클로징**: 질문 환영 · (해당 시) 7/24 개소식 소개 후보로 검토 부탁드립니다
- **Visual**: 좌(또는 전면) `<video controls playsinline poster="./assets/demo-poster.png">` · 우/하단 URL + 요약 박스
- **Notes**:
  - 발표 중 영상 재생 후 1문장 요약 → Q&A
  - 재생 실패 시 poster + URL로 대체
  - 필요하면 현장에서 라이브 1회 추가 클릭

## Design notes (Style C · warm-neutral)
- 배경 `#FAF8F5` · 패널 `#F0EBE3` · 액센트 테라코타 `#C45A3B`
- 본문 브라운 `#2D2A26` / 보조 `#6B6560` · 보더 `#DDD8D0`
- 표지 좌측 테라코타 액센트 바 · 카드 둥근 베이지 패널
- 기술 흐름: 가로 노드 + 테라코타 강조 노드 · 쿨 블루 금지
- 영상 슬라이드: 영상 영역이 주인공, 텍스트는 최소
- 본문 최소 11–12pt · 한 슬라이드 메시지 1개

## Assets
| 파일 | 용도 |
|------|------|
| `assets/demo-walkthrough.mp4` | 시연 영상 (~36s trim, H.264) |
| `assets/demo-poster.png` | 포스터 (PDF export) |
| `assets/demo-poster-start.png` | 시작 프레임 예비 |

## Out of scope
- 기존 14장 기술 브리핑 재사용
- 수식·문헌 표 전개
- v1 프로모션 검수 · Clerk/Neon/LLM 스택 소개

## Approval checklist
- [x] 스타일: `warm-neutral` (C)
- [x] 기술 스택·흐름 장표 반영 (Slide 6)
- [x] 시연 영상 트리밍 (~36s) + 자산
- [x] Stage 2 HTML 8장 · validate · design-gate Proceed · PDF 후보
- [ ] 사용자 최종 승인 (문구·영상·export)
