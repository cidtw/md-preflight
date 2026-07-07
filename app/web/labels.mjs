export const SOURCE_LABELS = {
  promotion_plan: "프로모션 계획",
  product_master: "상품 마스터",
  inventory: "재고",
};

export const COLUMN_LABELS = {
  benefit_condition: "혜택 조건",
  benefit_type: "혜택 유형",
  cost: "원가",
  end_date: "종료일",
  expected_demand: "예상 수요",
  inbound_date: "입고일",
  normal_price: "정상가",
  product_code: "상품코드",
  product_name: "상품명",
  promo_price: "행사가",
  promotion_id: "프로모션ID",
  start_date: "시작일",
  stock_qty: "재고수량",
};

export const RULE_LABELS = {
  DUPLICATE_MASTER_CODE: "중복 상품 코드",
  EXTREME_DISCOUNT_RATE: "과도한 할인율",
  INBOUND_DATE_CONFLICT: "입고일 충돌",
  INCOMPLETE_PRODUCT_MASTER: "마스터 핵심값 결측",
  INVENTORY_SHORTAGE_RISK: "재고 부족 위험",
  INVALID_DATE_RANGE: "잘못된 행사 기간",
  INVALID_PROMO_PRICE: "유효하지 않은 행사가",
  LOW_MARGIN_RATE: "낮은 마진율",
  MISSING_BENEFIT_CONDITION: "혜택 조건 누락",
  MISSING_PRODUCT_MASTER: "상품 마스터 누락",
};

export function displayLabel(key) {
  return RULE_LABELS[key] ?? COLUMN_LABELS[key] ?? key;
}
