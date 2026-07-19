/**
 * Demo presets:
 *  - VERIFIED_DEMO_STORES: thin client fallback only.
 *    Live census is loaded from GET /api/demo/verified-stores
 *    (anchor: 경기도 고양시 덕양구 세솔로 25).
 *  - DEMO_SCENARIOS: exploratory / dummy (optional Kakao address samples)
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
 * @property {string} [channel]
 * @property {number} [distance_m]
 */

/**
 * Client fallback when API census is unavailable.
 * Prefer live /api/demo/verified-stores in the UI.
 * @type {DemoScenario[]}
 */
export const VERIFIED_DEMO_STORES = [];

/**
 * Exploratory / dummy presets — free-form dong or Kakao address samples.
 * @type {DemoScenario[]}
 */
export const DEMO_SCENARIOS = [
  {
    id: "explore-admin-dong",
    tier: "explore",
    title: "탐색 · 행정동만 (지도 없음)",
    blurb: "정확한 위치 없이 행정동·상권 점수만 쓰는 경로 확인.",
    highlight: "use_precise_location=false",
    parameters: {
      product_name: "냉장 간편식",
      store_type: "convenience",
      store_size: "cv_s",
      avg_ticket: "t_le_8k",
      location_dong: "경기도 고양시 덕양구 행신동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "residential",
      accessibility: "main_road",
      daily_demand: 12,
      standard_lead_time_days: 2,
      service_level: "sl_95",
      order_day_pattern: "auto",
    },
  },
  {
    id: "explore-anchor-precise",
    tier: "explore",
    title: "탐색 · 앵커 주소 직접 입력",
    blurb: "세솔로 25를 매장 주소로 두고 geo/경쟁 옵션을 시험.",
    highlight: "precise + 선택 옵션",
    parameters: {
      product_name: "냉장 간편식 도시락",
      store_type: "convenience",
      store_size: "cv_s",
      avg_ticket: "t_le_8k",
      location_dong: "경기도 고양시 덕양구 행신동",
      use_precise_location: true,
      store_address: "경기도 고양시 덕양구 세솔로 25",
      consider_temp_foot_traffic: true,
      consider_competition_saturation: true,
      trade_area: "residential",
      accessibility: "main_road",
      daily_demand: 12,
      standard_lead_time_days: 1.5,
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
      location_dong: "경기도 고양시 덕양구 행신동",
      use_precise_location: false,
      store_address: "",
      consider_temp_foot_traffic: false,
      consider_competition_saturation: false,
      trade_area: "residential",
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
