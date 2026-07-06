/* ============================================================
   MD Preflight — MVP UI logic (dependency-free)
   Backend contract: POST /api/preflight (multipart) -> PreflightReport
   ============================================================ */

const FIELDS = [
  { key: "promotion_plan", role: "프로모션 계획", hint: "promotion_plan.xlsx / .csv" },
  { key: "product_master", role: "상품 마스터", hint: "product_master.xlsx / .csv" },
  { key: "inventory", role: "재고", hint: "inventory.xlsx / .csv" },
];
const ALLOWED = [".csv", ".xlsx"];
const MAX_BYTES = 5 * 1024 * 1024;

const state = {
  files: { promotion_plan: null, product_master: null, inventory: null },
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

function ext(name) {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i).toLowerCase();
}
function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/* ---------- toast ---------- */
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 4000);
}

/* ---------- view switching ---------- */
function showView(id) {
  ["view-upload", "view-loading", "view-result"].forEach((v) =>
    $(`#${v}`).classList.toggle("hidden", v !== id),
  );
}

/* ---------- dropzones ---------- */
function buildDropzones() {
  const grid = $("#dropzones");
  grid.innerHTML = "";
  FIELDS.forEach((f) => {
    const zone = el("label", "dropzone");
    zone.dataset.key = f.key;
    zone.innerHTML = `
      <p class="eyebrow">${f.key}</p>
      <span class="dz-role">${f.role}</span>
      <span class="dz-body caption mute">파일을 끌어다 놓거나 클릭해서 선택</span>
      <span class="dz-hint">${f.hint}</span>
      <input type="file" accept=".csv,.xlsx" />`;
    const input = zone.querySelector("input");

    input.addEventListener("change", () => {
      if (input.files[0]) setFile(f.key, input.files[0], zone);
    });
    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
      const file = e.dataTransfer.files[0];
      if (file) setFile(f.key, file, zone);
    });

    grid.appendChild(zone);
  });
}

function setFile(key, file, zone) {
  const body = zone.querySelector(".dz-body");
  zone.classList.remove("filled", "error");

  if (!ALLOWED.includes(ext(file.name))) {
    state.files[key] = null;
    zone.classList.add("error");
    body.className = "dz-body dz-err";
    body.textContent = `지원하지 않는 형식: ${ext(file.name) || "확장자 없음"} · .csv 또는 .xlsx만`;
    refreshRunBtn();
    return;
  }
  if (file.size > MAX_BYTES) {
    state.files[key] = null;
    zone.classList.add("error");
    body.className = "dz-body dz-err";
    body.textContent = `크기 초과: ${fmtSize(file.size)} · 최대 5MB`;
    refreshRunBtn();
    return;
  }

  state.files[key] = file;
  zone.classList.add("filled");
  body.className = "dz-body dz-file";
  body.textContent = `${file.name}`;
  const hint = zone.querySelector(".dz-hint");
  hint.className = "dz-check";
  hint.textContent = `✓ ${fmtSize(file.size)}`;
  refreshRunBtn();
}

function refreshRunBtn() {
  const ready = FIELDS.every((f) => state.files[f.key]);
  $("#run-btn").disabled = !ready;
}

/* ---------- run preflight ---------- */
async function runPreflight() {
  const fd = new FormData();
  FIELDS.forEach((f) => fd.append(f.key, state.files[f.key]));
  fd.append("use_llm", $("#use-llm").checked ? "true" : "false");

  showView("view-loading");
  try {
    const res = await fetch("/api/preflight", { method: "POST", body: fd });
    if (!res.ok) {
      let detail = `검수 요청 실패 (${res.status})`;
      try {
        const j = await res.json();
        if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch (_) {}
      throw new Error(detail);
    }
    const report = await res.json();
    renderReport(report);
    showView("view-result");
  } catch (err) {
    showView("view-upload");
    toast(err.message || "검수 중 오류가 발생했습니다.");
  }
}

/* ---------- render report ---------- */
const SEV_LABEL = { error: "error", warning: "warning", info: "info" };

function renderReport(r) {
  const s = r.summary;

  // download link
  const dl = $("#download-md");
  dl.href = `/api/preflight/runs/${r.run_id}/report.md`;

  // verdict
  const verdict = $("#verdict");
  const errCount = s.by_severity.error || 0;
  const warnCount = s.by_severity.warning || 0;
  if (s.passed) {
    verdict.className = "verdict pass";
    verdict.innerHTML = `검수 통과 <span class="v-sub">차단 이슈 없음 · 상품 ${s.checked_rows}건 검수</span>`;
  } else {
    verdict.className = "verdict fail";
    verdict.innerHTML = `검수 실패 <span class="v-sub">error ${errCount}건 · warning ${warnCount}건 · 상품 ${s.checked_rows}건 검수</span>`;
  }

  // stat tiles
  const stats = $("#stats");
  stats.innerHTML = "";
  const tiles = [
    { label: "전체 이슈", value: s.total_issues, cls: "" },
    { label: "error", value: errCount, cls: errCount ? "is-error" : "" },
    { label: "warning", value: warnCount, cls: warnCount ? "is-warning" : "" },
    { label: "검수 상품", value: s.checked_rows, cls: "" },
  ];
  tiles.forEach((t) => {
    const tile = el("div", `stat-tile ${t.cls}`);
    tile.append(el("div", "stat-value", String(t.value)));
    tile.append(el("div", "stat-label", t.label));
    stats.append(tile);
  });

  // issues
  $("#issue-count").textContent = r.issues.length;
  const list = $("#issues");
  list.innerHTML = "";
  if (r.issues.length === 0) {
    list.classList.remove("issue-list");
    list.append(el("div", "empty-clean", "✓ 검수 통과 — 발견된 이슈가 없습니다."));
  } else {
    list.classList.add("issue-list");
    const sorted = [...r.issues].sort((a, b) => sevRank(b.severity) - sevRank(a.severity) || a.code.localeCompare(b.code));
    sorted.forEach((iss) => list.append(renderIssue(iss)));
  }

  // ai summary + provenance
  const ai = $("#ai-summary");
  ai.className = "ai-panel has-badge";
  ai.innerHTML = "";
  const badge = el("span", `prov-badge ${r.generated_by === "llm" ? "llm" : "fallback"}`, r.generated_by);
  ai.append(badge);
  ai.append(el("div", "ai-text", r.ai_summary || "요약이 생성되지 않았습니다."));

  // checklist
  const cl = $("#checklist");
  cl.innerHTML = "";
  (r.checklist || []).forEach((item) => cl.append(el("li", null, item)));
  if (!r.checklist || r.checklist.length === 0) {
    cl.append(el("li", null, "체크리스트 항목이 없습니다."));
  }
}

function sevRank(sev) {
  return { error: 3, warning: 2, info: 1 }[sev] || 0;
}

function renderIssue(iss) {
  const row = el("div", `issue-row sev-${iss.severity}`);

  row.append(el("span", `badge sev-${iss.severity}`, SEV_LABEL[iss.severity] || iss.severity));
  row.append(el("span", "rule-chip", iss.code));

  const bodyEl = el("div", "issue-body");
  bodyEl.append(el("div", "issue-title", iss.title || iss.code));
  if (iss.message) bodyEl.append(el("div", "issue-msg", iss.message));

  const detail = el("div", "issue-detail");
  const entity = iss.entity || {};
  Object.entries(entity).forEach(([k, v]) => {
    const span = el("span");
    span.append(document.createTextNode(`${k}: `));
    span.append(el("b", null, String(v)));
    detail.append(span);
  });
  if (iss.observed != null) {
    const span = el("span");
    span.append(document.createTextNode("관측: "));
    span.append(el("b", null, String(iss.observed)));
    detail.append(span);
  }
  if (iss.expected != null) {
    const span = el("span");
    span.append(document.createTextNode("기대: "));
    span.append(el("b", null, String(iss.expected)));
    detail.append(span);
  }
  if (detail.childNodes.length) bodyEl.append(detail);
  if (iss.suggestion) {
    const sug = el("div", "issue-msg");
    sug.style.color = "var(--mute)";
    sug.textContent = `→ ${iss.suggestion}`;
    bodyEl.append(sug);
  }
  row.append(bodyEl);

  const loc = iss.location || {};
  const locText = [loc.file, loc.row != null ? `행 ${loc.row}` : null, loc.column]
    .filter(Boolean)
    .join(" · ");
  row.append(el("span", "issue-loc", locText));

  return row;
}

/* ---------- reset ---------- */
function resetToUpload() {
  state.files = { promotion_plan: null, product_master: null, inventory: null };
  buildDropzones();
  refreshRunBtn();
  showView("view-upload");
}

/* ---------- init ---------- */
buildDropzones();
$("#run-btn").addEventListener("click", runPreflight);
$("#back-btn").addEventListener("click", resetToUpload);
