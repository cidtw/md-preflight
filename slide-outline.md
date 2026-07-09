# MD Preflight 최종 발표자료

## Meta
- **Topic**: MD Preflight 프로젝트 성과 및 최종 아키텍처 발표
- **Target Audience**: 유통 비즈니스 이해관계자 및 테크 리드
- **Tone/Mood**: Restrained, Professional, Tech-focused
- **Slide Count**: 7 slides
- **Aspect Ratio**: 16:9
- **Style**: ppt-samsung-ir-restrained

## Slide Composition

### Slide 1 - Cover
- **Type**: Cover
- **Title**: 유통 프로모션 검수 엔진 'MD Preflight' 최종 발표
- **Subtitle**: 결정론적 규칙 검수와 AI 서술이 결합된 하이브리드 검수 시스템
- **Presenter**: 개발: 권태원 (SaaS Platformer)

### Slide 2 - Table of Contents
- **Type**: Contents
- **Items**:
  - 01. 도입 배경 및 문제 해결 (Problem & Solution)
  - 02. 핵심 아키텍처 (Stateless vs Isolated Path)
  - 03. 구현 및 검증 성과 (132개 테스트)
  - 04. 실배포 및 대시보드 라이브 시연 (Vercel & Neon Postgres)
  - 05. Q&A 및 맺음말

### Slide 3 - 도입 배경 및 문제 해결 (Problem & Solution)
- **Type**: Content
- **Key Message**: 수동 프로모션 검수 오류로 인한 비용 및 공수 손실을 0으로 차단합니다.
- **Details**:
  - **프로모션의 복잡성**: 가격, 기간, 마진, 재고, 증정 유형 등 다양한 실행 요소의 유기적 맞물림 필요
  - **오입력의 치명성**: 행사가 > 정상가, 마진 음수, 입고일 지연 등 사소한 오류가 점포 혼선 및 마진 악화 유발
  - **사전 검수 솔루션**: 등록 버튼을 누르기 전 계획/마스터/재고 3개 파일을 교차하여 실시간 자동 검수 수행

### Slide 4 - 핵심 아키텍처 (Stateless vs Isolated Path)
- **Type**: Content
- **Key Message**: 판정은 100% 결정론 규칙 엔진이, 서술과 이력 관리는 격리된 주변부가 수행합니다.
- **Details**:
  - **무상태 판정 경로 (Stateless Path)**: 동일 입력 시 항시 동일 결과 보장. LLM은 판정선 밖에 존재하며 결과 요약만 서술
  - **교체 가능한 서술 공급자**: OpenAI(Structured Outputs) 및 Anthropic 어댑터 자동 전환 및 로컬 Fallback 구성
  - **인증 및 이력 격리**: Neon Postgres 이력 적재 및 Clerk 세션 토큰 검증은 비로그인 검수 성능과 무관하게 격리 작동

### Slide 5 - 구현 및 검증 성과 (132개 테스트)
- **Type**: Statistics
- **Key Message**: 10개 검수 규칙 완결 및 132개 유닛 테스트 100% 통과로 무결성을 입증했습니다.
- **Details**:
  - **10대 핵심 룰셋**: 유효기간 검증, 마스터 매칭 누락, 할인율/마진율 임계치 위반, 입고 지연 등 완벽 감지
  - **132개 Pytest 케이스**: 정상가/원가 결측, 프롬프트 주입(Prompt Injection) 방어 계약 테스트 및 Clerk 세션 검증 완료
  - **정적 품질 보증**: `ruff` 및 `basedpyright` 정적 분석 0개 오류 통과

### Slide 6 - 실배포 및 대시보드 라이브 시연 (Vercel & Neon Postgres)
- **Type**: Timeline
- **Key Message**: 클라우드 실배포를 완료하고, 사용자별 검수 이력 통계를 한눈에 확인합니다.
- **Details**:
  - **Vercel 자동 배포**: 프로덕션 실환경 배포 완료 (`https://md-preflight.vercel.app`)
  - **이력 대시보드**: 누적 검수 횟수, 오류/경고 빈도, 패스율의 일/월별 추이를 보여주는 클라이언트 뷰 완결
  - **데모 데이터 시딩**: Neon Postgres에 실데이터 20개 런(Run) 이력을 적재하여 시연 대시보드 활성화

### Slide 7 - Closing
- **Type**: Closing
- **Message**: MD Preflight는 결정론적 안전성과 생성형 AI의 설명력을 결합한 가장 안전한 유통 운영 도구입니다.
- **Contact**: GitHub: github.com/cidtw/md-preflight | 이메일: taewon1119@gmail.com
