/**
 * Third-party demo presets — contrasting store contexts for live walkthroughs.
 * Pure data module; no DOM.
 */

/** @typedef {Record<string, string|number|boolean>} DemoParams */

/**
 * @typedef {object} DemoScenario
 * @property {string} id
 * @property {string} title
 * @property {string} blurb
 * @property {string} highlight  What a third-party should notice
 * @property {DemoParams} parameters
 * @property {boolean} [runImmediately]  If true, UI may submit after fill
 */

/** @type {DemoScenario[]} */
export const DEMO_SCENARIOS = [
  {
    id: "cv-capa-tight",
    title: "좁은 편의점 · CAPA",
    blurb: "건물 내 소형 편의점 — 공간 상한·다회 소량 발주가 잘 드러납니다.",
    highlight: "ROP 상한 · 월수금 다회 소량 · 쉬운 설명 문장",
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
    title: "대형마트 · 여유 공간",
    blurb: "대형 할인점 — 체급·객단가가 다른 채널 기본값과 발주 주기를 비교합니다.",
    highlight: "규모 밴드 기본 LT · 더 넉넉한 CAPA · Q/주기 차이",
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
    title: "상세 주소 · 일시 유동",
    blurb: "합정 일대 상세 주소 + 행사·유동 시설 스캔 — Kakao POI·수요 증분.",
    highlight: "geo 근거 블록 · event 배수 · 표준 vs 추천 비교",
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
    title: "상세 주소 · 경쟁 포화",
    blurb: "편의점 상권 내 동종·위협 경쟁 거리 — 시장 포화 수요 약화.",
    highlight: "경쟁 강도 · 수요 계수 ≤1 · ROP 하향",
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
    title: "유형·규모 불일치",
    blurb: "편의점 유형 + 대형 규모 — 연산은 규모·객단가 우선, 안내 문구 노출.",
    highlight: "guidance 배너 · size 우선 정책",
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
export function getDemoScenario(id) {
  return DEMO_SCENARIOS.find((s) => s.id === id);
}

/**
 * @returns {string[]}
 */
export function listDemoScenarioIds() {
  return DEMO_SCENARIOS.map((s) => s.id);
}
