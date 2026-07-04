#!/usr/bin/env bash
# MD Preflight — 30초 오프라인 데모.
# 서버를 기동해 clean(이슈 0) / dirty(10룰) 세트를 검수하고 Markdown 리포트를 뽑는다.
# LLM 키 없이도 동작한다(use_llm=false → 결정론적 fallback 서사).
set -euo pipefail

PORT="${PORT:-8099}"
BASE="http://127.0.0.1:${PORT}"
SAMPLES="data/samples"

cd "$(dirname "$0")"

pp() { python -c 'import sys,json; print(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))' 2>/dev/null || cat; }

echo "▶ 서버 기동 (port ${PORT}) ..."
uv run uvicorn app.main:app --port "${PORT}" --log-level warning &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# 헬스체크 대기 (최대 ~15s)
for _ in $(seq 1 30); do
  if curl -sf "${BASE}/api/preflight/health" >/dev/null 2>&1; then break; fi
  sleep 0.5
done
curl -sf "${BASE}/api/preflight/health" >/dev/null || { echo "✗ 서버 기동 실패"; exit 1; }
echo "✓ 서버 준비됨"

upload() { # $1 = clean|dirty
  curl -s -X POST "${BASE}/api/preflight" \
    -F use_llm=false \
    -F "promotion_plan=@${SAMPLES}/$1/promotion_plan.csv" \
    -F "product_master=@${SAMPLES}/$1/product_master.csv" \
    -F "inventory=@${SAMPLES}/$1/inventory.csv"
}

echo ""
echo "════════════════ 1) CLEAN 세트 (이슈 0건 기대) ════════════════"
upload clean | pp

echo ""
echo "════════════════ 2) DIRTY 세트 (10개 룰 전부 유발) ════════════════"
DIRTY_JSON="$(upload dirty)"
echo "${DIRTY_JSON}" | pp

RUN_ID="$(printf '%s' "${DIRTY_JSON}" | python -c 'import sys,json; print(json.load(sys.stdin)["run_id"])')"
echo ""
echo "════════════════ 3) Markdown 리포트 (run_id=${RUN_ID}) ════════════════"
curl -s "${BASE}/api/preflight/runs/${RUN_ID}/report.md"

echo ""
echo "✓ 데모 완료"
