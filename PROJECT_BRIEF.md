# MD Preflight Project Brief

MD Preflight는 유통 프로모션 등록 전, 행사 파일·상품 마스터·재고 파일을 업로드하면 가격·기간·재고·마진·증정조건 오류를 자동 검수하고, AI가 담당자용 실행 체크리스트를 생성하는 사전 검수 도구다.

## 핵심 문제
유통업에서 프로모션은 가격, 기간, 재고, 입고일, 증정 조건, POP, 종료 후 원복 등 여러 실행 요소가 동시에 맞아야 한다. 작은 오입력이나 누락이 점포 혼선, 고객 클레임, 재고 부족, 마진 악화로 이어질 수 있다.

## 설계 원칙
1. 검수 판단은 LLM이 아니라 deterministic rule engine이 수행한다.
2. LLM은 검수 결과를 실무자가 이해하기 쉬운 요약과 체크리스트로 변환한다.
3. MVP에서는 Excel/CSV 파일 3개만 사용한다.
4. 실시간 POS, ERP 연동, 로그인, 멀티테넌트, 수요예측은 구현하지 않는다.
5. 3주 안에 데모 가능한 완성도를 목표로 한다.

## 입력 파일
1. promotion_plan.xlsx
2. product_master.xlsx
3. inventory.xlsx

## 핵심 출력
1. 검수 요약
2. 이슈 상세 목록
3. AI 요약
4. 담당자 체크리스트
5. Markdown/PDF 보고서

## MVP 검수 룰
- INVALID_DATE_RANGE
- MISSING_PRODUCT_MASTER
- INVALID_PROMO_PRICE
- EXTREME_DISCOUNT_RATE
- LOW_MARGIN_RATE
- INVENTORY_SHORTAGE_RISK
- INBOUND_DATE_CONFLICT
- MISSING_BENEFIT_CONDITION