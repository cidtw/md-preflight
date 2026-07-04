# MVP Rule Matrix

## Active Rules

| Code | Default Severity | Description |
|---|---|---|
| `INVALID_DATE_RANGE` | `error` | 행사 시작일과 종료일이 파싱 가능하고 시작일이 종료일보다 늦지 않아야 함 |
| `MISSING_PRODUCT_MASTER` | `error` | 프로모션 상품 코드가 상품 마스터에 존재해야 함 |
| `INVALID_PROMO_PRICE` | `error` | 행사가는 0보다 커야 하고 정상가를 초과하면 안 됨 |
| `EXTREME_DISCOUNT_RATE` | `warning` | 할인율이 설정된 최대 임계값 이상이면 경고 |
| `LOW_MARGIN_RATE` | `warning` | 마진율이 최소 임계값보다 낮으면 경고, 음수면 오류로 승격 |
| `INVENTORY_SHORTAGE_RISK` | `warning` | 예상 수요가 재고 수량을 초과하면 경고 |
| `INBOUND_DATE_CONFLICT` | `warning` | 입고일이 행사 시작일보다 늦으면 경고 |
| `MISSING_BENEFIT_CONDITION` | `error` | 혜택 유형이 있으면 혜택 조건도 함께 존재해야 함 |
