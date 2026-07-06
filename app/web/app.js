import {
  buildEditedCsvFilename,
  isCsvFilename,
  isSpreadsheetFilename,
  parseCsv,
  toCsv,
} from "./csv_tools.mjs";

const FIELDS = [
  { key: "promotion_plan", role: "프로모션 계획", hint: "promotion_plan.xlsx / .csv" },
  { key: "product_master", role: "상품 마스터", hint: "product_master.xlsx / .csv" },
  { key: "inventory", role: "재고", hint: "inventory.xlsx / .csv" },
];
const ALLOWED = [".csv", ".xlsx"];
const MAX_BYTES = 5 * 1024 * 1024;
const SOURCE_LABELS = {
  promotion_plan: "프로모션 계획",
  product_master: "상품 마스터",
  inventory: "재고",
};

const state = {
  files: { promotion_plan: null, product_master: null, inventory: null },
  parsed: {
    promotion_plan: null,
    product_master: null,
    inventory: null,
  },
  result: null,
  fileIssues: {},
  highlightTarget: null,
  sourceCatalog: [],
  selectedSourceId: "upload",
  appliedChecklistItems: new Set(),
  dismissedChecklistItems: new Set(),
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
      if (input.files[0]) {
        void setFile(f.key, input.files[0], zone);
      }
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
      if (file) {
        void setFile(f.key, file, zone);
      }
    });

    grid.appendChild(zone);
  });
}

async function setFile(key, file, zone) {
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
  state.parsed[key] = await buildParsedState(file);
  zone.classList.add("filled");
  body.className = "dz-body dz-file";
  body.textContent = `${file.name}`;
  const hint = zone.querySelector(".dz-hint");
  hint.className = "dz-check";
  hint.textContent = `✓ ${fmtSize(file.size)}`;
  refreshRunBtn();
  renderFileEditors();
}

function refreshRunBtn() {
  const ready = FIELDS.every((f) => state.files[f.key]);
  $("#run-btn").disabled = !ready;
}

/* ---------- run preflight ---------- */
async function runPreflight(filesOverride = null) {
  const fd = new FormData();
  FIELDS.forEach((f) => {
    const file = filesOverride?.[f.key] ?? state.files[f.key];
    fd.append(f.key, file);
  });
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
    state.result = report;
    state.fileIssues = groupIssuesByFile(report.issues);
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
    list.append(el("div", "empty-clean", "✓ 검수 통과 — 발견된 문제가 없습니다."));
  } else {
    list.classList.add("issue-list");
    const sorted = [...r.issues].sort((a, b) => sevRank(b.severity) - sevRank(a.severity) || a.code.localeCompare(b.code));
    sorted.forEach((iss) => list.append(renderIssue(iss)));
  }

  // ai summary + provenance
  const ai = $("#ai-summary");
  const isFallback = r.generated_by !== "llm";
  ai.className = `ai-panel has-badge ${isFallback ? "is-fallback" : "is-llm"}`;
  ai.innerHTML = "";
  const badge = el("span", `prov-badge ${r.generated_by === "llm" ? "llm" : "fallback"}`, r.generated_by);
  const note = el(
    "div",
    "ai-note",
    isFallback
      ? "표준 요약 · 미리 정해둔 규칙 결과를 바탕으로 정리한 문장입니다."
      : "AI 요약 · 이번 검수에서 먼저 봐야 할 포인트를 정리했습니다.",
  );
  ai.append(note);
  ai.append(badge);
  ai.append(el("div", "ai-text", r.ai_summary || "요약이 생성되지 않았습니다."));

  renderFileSummaries(r.file_summaries || []);

  // checklist
  renderChecklist(r);
  renderFileEditors();
  refreshEditedActions();
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
  if (iss.location?.file) {
    const jump = el("button", "btn btn-ghost issue-jump-btn", "파일에서 보기");
    jump.type = "button";
    jump.addEventListener("click", () => jumpToIssueLocation(iss.location));
    bodyEl.append(jump);
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
  state.parsed = { promotion_plan: null, product_master: null, inventory: null };
  state.result = null;
  state.fileIssues = {};
  state.highlightTarget = null;
  state.appliedChecklistItems = new Set();
  state.dismissedChecklistItems = new Set();
  buildDropzones();
  refreshRunBtn();
  refreshEditedActions();
  showView("view-upload");
}

/* ---------- theme (light / dark / system) ---------- */
const mql = window.matchMedia("(prefers-color-scheme: dark)");

function applyTheme(pref) {
  const dark = pref === "dark" || (pref === "system" && mql.matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.dataset.themePref = pref;
  document.querySelectorAll(".theme-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.themeSet === pref),
  );
}

function initTheme() {
  let pref = "system";
  try {
    pref = localStorage.getItem("mdp-theme") || "system";
  } catch (_) {}
  applyTheme(pref);
  document.querySelectorAll(".theme-btn").forEach((b) =>
    b.addEventListener("click", () => {
      const p = b.dataset.themeSet;
      try {
        localStorage.setItem("mdp-theme", p);
      } catch (_) {}
      applyTheme(p);
    }),
  );
  // 시스템 모드일 때 OS 테마 변경을 실시간 반영
  mql.addEventListener("change", () => {
    if ((document.documentElement.dataset.themePref || "system") === "system") {
      applyTheme("system");
    }
  });
}

/* ---------- init ---------- */
buildDropzones();
initTheme();
void loadSources();
$("#run-btn").addEventListener("click", () => {
  void runPreflight();
});
$("#back-btn").addEventListener("click", resetToUpload);
$("#export-edited-top").addEventListener("click", exportAllEditedFiles);
$("#rerun-edited-top").addEventListener("click", () => {
  void rerunWithEditedFiles();
});

async function buildParsedState(file) {
  if (isCsvFilename(file.name)) {
    try {
      const parsed = parseCsv(await file.text());
      return {
        kind: "csv",
        editable: true,
        headers: parsed.headers,
        rows: parsed.rows,
        originalRows: parsed.rows.map((row) => [...row]),
        edits: new Set(),
        dirty: false,
        sourceName: file.name,
      };
    } catch (error) {
      toast(error.message || "CSV 파싱에 실패했습니다.");
      return {
        kind: "csv",
        editable: false,
        headers: [],
        rows: [],
        originalRows: [],
        edits: new Set(),
        dirty: false,
        sourceName: file.name,
        parseError: "CSV 파싱 실패",
      };
    }
  }
  if (isSpreadsheetFilename(file.name)) {
    return {
      kind: "xlsx",
      editable: false,
      headers: [],
      rows: [],
      originalRows: [],
      edits: new Set(),
      dirty: false,
      sourceName: file.name,
    };
  }
  return null;
}

function groupIssuesByFile(issues) {
  return issues.reduce((acc, issue) => {
    const file = issue.location?.file;
    if (!file) {
      return acc;
    }
    const bucket = acc[file] || [];
    bucket.push(issue);
    acc[file] = bucket;
    return acc;
  }, {});
}

function renderFileSummaries(fileSummaries) {
  let host = $("#ai-file-summaries");
  if (!host) {
    host = el("div", "ai-file-summaries");
    host.id = "ai-file-summaries";
    $("#ai-summary").append(host);
  }
  host.innerHTML = "";
  fileSummaries.forEach((summary) => {
    const card = el("div", "ai-file-card");
    card.append(el("div", "ai-file-name", summary.file));
    card.append(el("div", "ai-file-meta", `${summary.issue_count}건`));
    card.append(el("div", "ai-file-headline", summary.headline));
    host.append(card);
  });
}

function renderFileEditors() {
  const host = $("#file-editors");
  if (!host) {
    return;
  }
  host.innerHTML = "";
  FIELDS.forEach((field) => {
    const parsed = state.parsed[field.key];
    const details = el("details", "file-editor");
    details.open = field.key === state.highlightTarget?.file || host.children.length === 0;
    const summary = el("summary", "file-editor-summary");
    const rowCount = parsed?.rows?.length || 0;
    const issueCount = state.fileIssues[field.key]?.length || 0;
    summary.append(el("span", "file-editor-title", SOURCE_LABELS[field.key]));
    summary.append(el("span", "file-editor-meta", `${rowCount}행 · 이슈 ${issueCount}건`));
    if (parsed?.kind === "xlsx") {
      summary.append(el("span", "file-editor-badge readonly", "xlsx 보기 전용"));
    } else if (parsed?.dirty) {
      summary.append(el("span", "file-editor-badge dirty", "수정됨"));
    } else if (parsed?.editable) {
      summary.append(el("span", "file-editor-badge editable", "CSV 편집 가능"));
    }
    details.append(summary);

    const body = el("div", "file-editor-body");
    if (!parsed) {
      body.append(el("p", "caption mute", "아직 업로드된 파일이 없습니다."));
    } else if (parsed.kind === "xlsx") {
      body.append(el("p", "caption mute", "xlsx는 보기 전용입니다. 편집하려면 CSV로 다시 업로드하세요."));
    } else if (!parsed.editable) {
      body.append(el("p", "caption mute", parsed.parseError || "이 파일은 편집할 수 없습니다."));
    } else {
      body.append(renderFileEditorActions(field.key, parsed));
      body.append(buildEditorTable(field.key, parsed));
    }
    details.append(body);
    host.append(details);
  });
}

function renderFileEditorActions(fileKey, parsed) {
  const wrap = el("div", "file-editor-actions");
  const exportButton = el("button", "btn btn-secondary", "수정본 CSV 내보내기");
  exportButton.type = "button";
  exportButton.disabled = !parsed.dirty;
  exportButton.addEventListener("click", () => exportParsedFile(fileKey));
  wrap.append(exportButton);

  const status = el(
    "span",
    "caption mute",
    parsed.dirty ? "편집한 셀을 포함해 CSV로 내보낼 수 있습니다." : "편집 후 수정본 내보내기가 활성화됩니다.",
  );
  wrap.append(status);
  return wrap;
}

function buildEditorTable(fileKey, parsed) {
  const scroller = el("div", "file-editor-table-wrap");
  const table = el("table", "file-editor-table");
  const thead = el("thead");
  const headRow = el("tr");
  headRow.append(el("th", "file-editor-rowhead", "행"));
  parsed.headers.forEach((header) => headRow.append(el("th", null, header)));
  thead.append(headRow);
  table.append(thead);

  const tbody = el("tbody");
  parsed.rows.forEach((row, rowIndex) => {
    const tr = el("tr");
    const csvRowNumber = rowIndex + 2;
    tr.dataset.file = fileKey;
    tr.dataset.row = String(csvRowNumber);
    const rowHead = el("th", "file-editor-rowhead", String(csvRowNumber));
    tr.append(rowHead);
    row.forEach((value, columnIndex) => {
      const td = el("td");
      const input = el("input", "file-editor-input");
      input.value = value;
      input.dataset.file = fileKey;
      input.dataset.row = String(csvRowNumber);
      input.dataset.column = parsed.headers[columnIndex];
      input.addEventListener("input", () => updateParsedCell(fileKey, rowIndex, columnIndex, input.value));
      if (isEditedCell(parsed, rowIndex, columnIndex)) {
        td.classList.add("is-edited");
      }
      if (matchesHighlight(fileKey, csvRowNumber, parsed.headers[columnIndex])) {
        td.classList.add("is-highlighted");
      }
      td.append(input);
      tr.append(td);
    });
    if (matchesHighlight(fileKey, csvRowNumber, state.highlightTarget?.column || null)) {
      tr.classList.add("is-highlighted");
    }
    tbody.append(tr);
  });
  table.append(tbody);
  scroller.append(table);
  return scroller;
}

function updateParsedCell(fileKey, rowIndex, columnIndex, value) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv") {
    return;
  }
  parsed.rows[rowIndex][columnIndex] = value;
  const key = `${rowIndex},${columnIndex}`;
  if (parsed.originalRows[rowIndex][columnIndex] === value) {
    parsed.edits.delete(key);
  } else {
    parsed.edits.add(key);
  }
  parsed.dirty = parsed.edits.size > 0;
  refreshEditedActions();
  renderFileEditors();
}

function isEditedCell(parsed, rowIndex, columnIndex) {
  return parsed.edits.has(`${rowIndex},${columnIndex}`);
}

function matchesHighlight(fileKey, row, column) {
  if (!state.highlightTarget) {
    return false;
  }
  return (
    state.highlightTarget.file === fileKey &&
    state.highlightTarget.row === row &&
    (column == null || state.highlightTarget.column == null || state.highlightTarget.column === column)
  );
}

function jumpToIssueLocation(location) {
  if (!location.file || !location.row) {
    return;
  }
  state.highlightTarget = {
    file: location.file,
    row: location.row,
    column: location.column || null,
  };
  renderFileEditors();
  requestAnimationFrame(() => {
    const target = document.querySelector(
      `[data-file="${location.file}"][data-row="${location.row}"][data-column="${location.column || ""}"]`,
    ) || document.querySelector(`[data-file="${location.file}"][data-row="${location.row}"]`);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      if (target.focus) {
        target.focus();
      }
    }
  });
}

function exportParsedFile(fileKey) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv" || !parsed.dirty) {
    return;
  }
  const blob = new Blob([toCsv(parsed.headers, parsed.rows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = buildEditedCsvFilename(fileKey);
  link.click();
  URL.revokeObjectURL(url);
}

function exportAllEditedFiles() {
  FIELDS.forEach((field) => {
    const parsed = state.parsed[field.key];
    if (parsed?.kind === "csv" && parsed.dirty) {
      exportParsedFile(field.key);
    }
  });
}

function refreshEditedActions() {
  const hasDirtyFiles = FIELDS.some((field) => state.parsed[field.key]?.dirty);
  $("#export-edited-top").disabled = !hasDirtyFiles;
  $("#rerun-edited-top").disabled = !hasDirtyFiles;
}

function renderChecklist(report) {
  const host = $("#checklist");
  host.innerHTML = "";
  const items = report.checklist_items || [];
  const visibleItems = items.filter((item) => !state.dismissedChecklistItems.has(checklistItemKey(item)));
  if (visibleItems.length > 0) {
    visibleItems.forEach((item) => host.append(buildChecklistItemElement(item)));
    return;
  }
  (report.checklist || []).forEach((item) => host.append(el("li", null, item)));
  if ((!report.checklist || report.checklist.length === 0) && visibleItems.length === 0) {
    host.append(el("li", null, "체크리스트 항목이 없습니다."));
  }
}

function buildChecklistItemElement(item) {
  const itemKey = checklistItemKey(item);
  const li = el("li", `checklist-review ${state.appliedChecklistItems.has(itemKey) ? "is-applied" : ""}`);
  const body = el("div", "checklist-review-body");
  body.append(el("div", "checklist-review-title", `[${item.code}] ${item.rationale}`));
  body.append(el("div", "checklist-review-meta", `${item.file} · 행 ${item.row ?? "-"} · ${item.column ?? "-"}`));
  body.append(el("div", "checklist-review-values", `현재값: ${item.current ?? "-"} · 권장값: ${item.suggested ?? "직접 수정 필요"}`));
  li.append(body);

  const actions = el("div", "checklist-review-actions");
  const apply = el("button", "btn btn-secondary", state.appliedChecklistItems.has(itemKey) ? "적용됨" : "적용");
  apply.type = "button";
  apply.disabled = state.appliedChecklistItems.has(itemKey) || !canApplyChecklistItem(item);
  apply.addEventListener("click", () => applyChecklistItem(item));
  actions.append(apply);

  const manual = el("button", "btn btn-ghost", "직접 수정");
  manual.type = "button";
  manual.addEventListener("click", () => jumpToIssueLocation(item));
  actions.append(manual);

  const dismiss = el("button", "btn btn-ghost", "무시");
  dismiss.type = "button";
  dismiss.addEventListener("click", () => {
    state.dismissedChecklistItems.add(itemKey);
    renderChecklist(state.result);
  });
  actions.append(dismiss);
  li.append(actions);
  return li;
}

function checklistItemKey(item) {
  return [item.code, item.file, item.row ?? "-", item.column ?? "-"].join(":");
}

function canApplyChecklistItem(item) {
  if (item.suggested == null || item.row == null || item.column == null) {
    return false;
  }
  const parsed = state.parsed[item.file];
  if (!parsed || parsed.kind !== "csv" || !parsed.editable) {
    return false;
  }
  const rowIndex = item.row - 2;
  const columnIndex = parsed.headers.indexOf(item.column);
  return rowIndex >= 0 && rowIndex < parsed.rows.length && columnIndex >= 0;
}

function applyChecklistItem(item) {
  if (!canApplyChecklistItem(item) || item.suggested == null || item.row == null || item.column == null) {
    return;
  }
  const parsed = state.parsed[item.file];
  const rowIndex = item.row - 2;
  const columnIndex = parsed.headers.indexOf(item.column);
  updateParsedCell(item.file, rowIndex, columnIndex, item.suggested);
  state.appliedChecklistItems.add(checklistItemKey(item));
  jumpToIssueLocation(item);
  renderChecklist(state.result);
}

async function rerunWithEditedFiles() {
  const overrides = {};
  await Promise.all(
    FIELDS.map(async (field) => {
      const parsed = state.parsed[field.key];
      if (parsed?.kind === "csv" && parsed.dirty) {
        overrides[field.key] = new File(
          [toCsv(parsed.headers, parsed.rows)],
          state.files[field.key]?.name || `${field.key}.csv`,
          { type: "text/csv" },
        );
      }
    }),
  );
  await runPreflight(overrides);
}

async function loadSources() {
  try {
    const response = await fetch("/api/preflight/sources");
    if (!response.ok) {
      return;
    }
    state.sourceCatalog = await response.json();
    renderSourcePicker();
  } catch (_) {}
}

function renderSourcePicker() {
  const host = $("#source-picker");
  if (!host) {
    return;
  }
  host.innerHTML = "";
  const chips = el("div", "source-chip-list");
  const panel = el("div", "source-preview");
  state.sourceCatalog.forEach((source) => {
    const button = el("button", `source-chip is-${source.status}`, source.label);
    button.type = "button";
    button.setAttribute("aria-pressed", String(state.selectedSourceId === source.id));
    button.classList.toggle("active", state.selectedSourceId === source.id);
    button.addEventListener("click", () => {
      state.selectedSourceId = source.id;
      renderSourcePicker();
    });
    chips.append(button);
    if (source.status !== "available") {
      const badge = el("span", "source-chip-badge", "곧 지원");
      button.append(badge);
    }
    if (state.selectedSourceId === source.id) {
      panel.append(el("div", "source-preview-title", source.label));
      panel.append(el("div", "source-preview-body", source.description));
      const status = el(
        "div",
        "caption mute",
        source.status === "available" ? "현재 업로드 경로를 사용할 수 있습니다." : "예정된 소스입니다. 실제 연결은 아직 지원하지 않습니다.",
      );
      panel.append(status);
      if (source.auth_fields.length > 0) {
        const list = el("ul", "source-preview-list");
        source.auth_fields.forEach((field) => list.append(el("li", null, field)));
        panel.append(list);
      }
    }
  });
  host.append(chips);
  host.append(panel);

  const dropzones = $("#dropzones");
  if (dropzones) {
    dropzones.classList.toggle("hidden", state.selectedSourceId !== "upload");
  }
}
