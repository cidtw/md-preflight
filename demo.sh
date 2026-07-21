#!/usr/bin/env bash
# Third-party / local demo smoke for 발주맞춤 · OrderFit.
# Usage:
#   ./demo.sh                 # hit local http://127.0.0.1:8000
#   ./demo.sh --prod          # hit https://baljumatch.vercel.app
#   BASE_URL=https://… ./demo.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
if [[ "${1:-}" == "--prod" ]]; then
  BASE_URL="https://baljumatch.vercel.app"
fi

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
ok() { printf '  ✓ %s\n' "$*"; }
fail() { printf '  ✗ %s\n' "$*" >&2; exit 1; }

bold "발주맞춤 · OrderFit demo smoke → ${BASE_URL}"

health="$(curl -fsS -m 20 "${BASE_URL}/api/health")"
ver="$(printf '%s' "$health" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get("status")=="ok" and d.get("service")=="rop-adjust"; print(d.get("version","?"))')" \
  || fail "health"
ok "health ${ver}"

curl -fsS -m 20 -o /dev/null "${BASE_URL}/" || fail "index"
ok "index 200"

curl -fsS -m 20 -o /dev/null "${BASE_URL}/static/app.js" || fail "app.js"
curl -fsS -m 20 -o /dev/null "${BASE_URL}/static/demo_scenarios.mjs" || fail "demo_scenarios.mjs"
curl -fsS -m 20 -o /dev/null "${BASE_URL}/static/favicon.svg" || fail "favicon"
ok "static modules + favicon"

eval_json="$(curl -fsS -m 30 -X POST "${BASE_URL}/api/evaluate" \
  -H 'content-type: application/json' \
  -d '{
    "parameters": {
      "product_name": "냉장 간편식",
      "store_type": "convenience",
      "store_size": "cv_s",
      "avg_ticket": "t_le_8k",
      "location_dong": "서울시 마포구 서교동",
      "trade_area": "office",
      "accessibility": "indoor",
      "daily_demand": 12,
      "standard_lead_time_days": 2
    }
  }')"
printf '%s' "$eval_json" | python3 -c '
import sys, json
d = json.load(sys.stdin)
assert d.get("recommendation"), "missing recommendation"
assert d.get("comparison", {}).get("rows"), "missing comparison"
assert len(d.get("evidence", [])) == 4, "expected 4 evidence blocks"
assert "calc" in d and "recommended_rop" in d["calc"]
rec = d["recommendation"][:72]
rop = d["calc"]["recommended_rop"]
print("ROP=%s · rec=%s…" % (rop, rec))
' || fail "evaluate"
ok "evaluate (default convenience)"

geo_json="$(curl -fsS -m 45 -X POST "${BASE_URL}/api/evaluate" \
  -H 'content-type: application/json' \
  -d '{
    "parameters": {
      "product_name": "아이스 커피",
      "store_type": "convenience",
      "store_size": "cv_m",
      "avg_ticket": "t_le_8k",
      "location_dong": "서울시 마포구 합정동",
      "use_precise_location": true,
      "store_address": "서울 마포구 양화로 45",
      "consider_temp_foot_traffic": true,
      "trade_area": "tourist",
      "accessibility": "main_road",
      "daily_demand": 40,
      "standard_lead_time_days": 1,
      "service_level": "sl_99"
    }
  }')"
printf '%s' "$geo_json" | python3 -c '
import sys, json
d = json.load(sys.stdin)
g = d["calc"]["geo"]
assert g.get("enabled") is True
assert g.get("provider") == "kakao"
fb = "fallback" if g.get("used_fallback") else "live"
print("geo %s · fti=%s · event_mult=%s" % (
    fb, g.get("foot_traffic_index"), g.get("event_demand_multiplier")))
' || fail "evaluate geo"
ok "evaluate (precise + event, 200)"

bold "All demo checks passed."
echo "Open: ${BASE_URL}/"
echo "Tip: welcome 화면 「시연 시나리오」 카드로 제3자 데모 경로를 바로 채울 수 있습니다."
