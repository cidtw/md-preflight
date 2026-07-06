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

export function displayLabel(key) {
  return COLUMN_LABELS[key] ?? key;
}
