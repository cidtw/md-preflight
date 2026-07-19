/**
 * Demo presets:
 *  - VERIFIED_DEMO_STORES: presentation-primary (1–2 measured profiles)
 *  - DEMO_SCENARIOS: exploratory / dummy (region + optional Kakao address)
 *
 * Selecting a *real* store via Kakao (precise location) is still available in
 * the wizard; that path does not attach verified demand/ROP walkthrough data.
 */

/** @typedef {Record<string, string|number|boolean>} DemoParams */

/**
 * @typedef {object} DemoScenario
 * @property {string} id
 * @property {string} title
 * @property {string} blurb
 * @property {string} highlight
 * @property {DemoParams} parameters
 * @property {boolean} [runImmediately]
 * @property {string} [storeLabel]
 * @property {string} [verificationNote]
 * @property {Record<string, string|number|boolean>} [expected]
 * @property {"verified"|"explore"} [tier]
 */

/** @type {DemoScenario[]} */
export const VERIFIED_DEMO_STORES = [
  {
    id: "verified-a-yeoksam-cvs",
    tier: "verified",
    title: "시연 A · 역삼 오피스 편의점",
    storeLabel: "(무인)편의점 · 소형 · 역삼1동 · 건물 내",
    blurb:
      "검증 프로필: 오피스·건물 내·냉장 간편식. 이론 ROP가 CAPA에 막혀 다회 소량 발주가 드러납니다.",
    highlight: "CAPA 캡 · ROP 31.2 · SS 7.2 · 월수금 · Z 1.65→2.38",
    verificationNote:
      "파라미터·발주 체인 실측 검증 (행정동 경로). POS 연동 아님. 지도 API 없이 재현.",
    expected: {
      recommended_rop: 31.2,
      store_safety_stock: 7.2,
      suggested_order_qty: 28,
      order_days_label: "월·수·금",
      capa_capped: true,
    },
    parameters: {
      product_name: "냉장 간편식 도시락",
      store_type: "convenience",
      store_size: "cv_s",
      avg_ticket: "t_le_8k",
      location_dong: "서울시 강남구 역삼1동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "office",
      accessibility: "indoor",
      daily_demand: 12,
      standard_lead_time_days: 2,
      service_level: "sl_95",
      order_day_pattern: "auto",
    },
  },
  {
    id: "verified-b-yeoksam-super",
    tier: "verified",
    title: "시연 B · 역삼 주거 슈퍼",
    storeLabel: "일반 슈퍼 · 주거 밀착 · 역삼1동 · 대로변",
    blurb:
      "검증 프로필: 주거·대로·상온 라면. 같은 SL 95%여도 캡 없이 맥락 SS가 반영됩니다.",
    highlight: "캡 없음 · ROP 37.04 · SS 21.04 · 월목 · buffer 0",
    verificationNote:
      "A 대조군 실측 검증. POS 연동 아님. 동일 행정동·다른 체급 비교.",
    expected: {
      recommended_rop: 37.04,
      store_safety_stock: 21.04,
      suggested_order_qty: 28,
      order_days_label: "월·목",
      capa_capped: false,
    },
    parameters: {
      product_name: "상온 라면",
      store_type: "supermarket",
      store_size: "sm",
      avg_ticket: "t_8k_15k",
      location_dong: "서울시 강남구 역삼1동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "residential",
      accessibility: "main_road",
      daily_demand: 8,
      standard_lead_time_days: 2,
      service_level: "sl_95",
      order_day_pattern: "auto",
    },
  },
];

/**
 * Exploratory / dummy presets — free-form dong or Kakao address samples.
 * Not the primary presentation path.
 * @type {DemoScenario[]}
 */
export const DEMO_SCENARIOS = [
  {
    id: "cv-capa-tight",
    tier: "explore",
    title: "탐색 · 좁은 편의점 CAPA",
    blurb: "더미 행정동 경로 — 공간 상한·다회 소량 발주 패턴 탐색.",
    highlight: "ROP 상한 · 월수금 · 쉬운 설명",
    parameters: {
      product_name: "냉장 간편식",
      store_type: "convenience",
      store_size: "cv_s",
      avg_ticket: "t_le_8k",
      location_dong: "서울시 마포구 서교동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "office",
      accessibility: "indoor",
      daily_demand: 12,
      standard_lead_time_days: 2,
      service_level: "sl_95",
      order_day_pattern: "auto",
    },
  },
  {
    id: "hyper-scale",
    tier: "explore",
    title: "탐색 · 대형마트 여유",
    blurb: "더미 채널 비교 — 규모 밴드·발주 주기 차이.",
    highlight: "여유 CAPA · Q/주기",
    parameters: {
      product_name: "생수 2L 6입",
      store_type: "hypermarket",
      store_size: "hyper",
      avg_ticket: "t_45k_55k",
      location_dong: "경기도 성남시 분당구 정자동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "suburban",
      accessibility: "main_road",
      daily_demand: 80,
      standard_lead_time_days: 3,
      service_level: "sl_95",
      order_day_pattern: "auto",
    },
  },
  {
    id: "precise-event",
    tier: "explore",
    title: "탐색 · 상세 주소·일시 유동",
    blurb: "Kakao 주소 샘플 + 행사 스캔 — 키 있을 때만 geo/event 근거.",
    highlight: "geo · event 배수 (탐색용 주소)",
    parameters: {
      product_name: "아이스 커피",
      store_type: "convenience",
      store_size: "cv_m",
      avg_ticket: "t_le_8k",
      location_dong: "서울시 마포구 합정동",
      use_precise_location: true,
      store_address: "서울 마포구 양화로 45",
      consider_temp_foot_traffic: true,
      consider_competition_saturation: false,
      trade_area: "tourist",
      accessibility: "main_road",
      daily_demand: 40,
      standard_lead_time_days: 1,
      service_level: "sl_99",
      order_day_pattern: "auto",
    },
  },
  {
    id: "precise-competition",
    tier: "explore",
    title: "탐색 · 상세 주소·경쟁 포화",
    blurb: "Kakao 주소 샘플 + 경쟁 스캔 — 수요 계수 ≤1 탐색.",
    highlight: "경쟁 강도 · ROP 하향 (탐색용)",
    parameters: {
      product_name: "생수 500ml",
      store_type: "convenience",
      store_size: "cv_s",
      avg_ticket: "t_le_8k",
      location_dong: "서울시 마포구 합정동",
      use_precise_location: true,
      store_address: "서울 마포구 양화로 45",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: true,
      trade_area: "office",
      accessibility: "main_road",
      daily_demand: 30,
      standard_lead_time_days: 2,
      service_level: "sl_95",
      order_day_pattern: "auto",
    },
  },
  {
    id: "mismatch-guidance",
    tier: "explore",
    title: "탐색 · 유형·규모 불일치",
    blurb: "더미 불일치 guidance 확인용.",
    highlight: "guidance · size 우선",
    parameters: {
      product_name: "즉석밥",
      store_type: "convenience",
      store_size: "hyper",
      avg_ticket: "t_45k_55k",
      location_dong: "서울시 강남구 역삼동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "office",
      accessibility: "alley",
      daily_demand: 25,
      standard_lead_time_days: 2,
      service_level: "sl_90",
      order_day_pattern: "weekly_mon",
    },
  },
];

/**
 * @param {string} id
 * @returns {DemoScenario | undefined}
 */
export function getVerifiedDemoStore(id) {
  return VERIFIED_DEMO_STORES.find((s) => s.id === id);
}

/**
 * @param {string} id
 * @returns {DemoScenario | undefined}
 */
export function getDemoScenario(id) {
  return (
    getVerifiedDemoStore(id) || DEMO_SCENARIOS.find((s) => s.id === id)
  );
}

/**
 * @returns {string[]}
 */
export function listDemoScenarioIds() {
  return [
    ...VERIFIED_DEMO_STORES.map((s) => s.id),
    ...DEMO_SCENARIOS.map((s) => s.id),
  ];
}

/**
 * @returns {string[]}
 */
export function listVerifiedDemoStoreIds() {
  return VERIFIED_DEMO_STORES.map((s) => s.id);
}
