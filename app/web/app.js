import {
  buildEditedCsvFilename,
  buildLargeFileWarning,
  isCsvFilename,
  isSpreadsheetFilename,
  parseCsv,
  shouldDisableInlineEditing,
  toCsv,
} from "./csv_tools.mjs";
import {
  applyParsedCellEdit,
  buildHighlightTargets,
  cellEditKey,
  deleteParsedColumn,
  deleteParsedRow,
  revertParsed,
  sanitizeChecklistCellValue,
} from "./editor_state.mjs";
import {
  hasClerkMode,
  isSignedIn,
  isStubAuthAvailable,
} from "./auth_helpers.mjs";
import { getUploadLimits } from "./config_helpers.mjs";
import { renderHistoryDashboard } from "./history_dashboard.mjs";
import { buildHistoryRunsUrl, buildHistoryUrl, normalizeGranularity } from "./history_helpers.mjs";
import { SOURCE_LABELS, displayLabel } from "./labels.mjs";
import { bindWordmarkHome } from "./nav_helpers.mjs";
import { checklistItemKey, diffIssueKeys, issueKey } from "./review_status.mjs";
import { buildServiceRequestUrl } from "./source_request.mjs";
import { $, el, ext, fmtSize, toast, showView } from "./dom_util.mjs";
import { initTheme } from "./theme.mjs";
import { createAuthUi } from "./auth_ui.mjs";
import { createIssueView, groupIssuesByFile } from "./issue_view.mjs";
import { createReportView } from "./report_view.mjs";

const FIELDS = [
  { key: "promotion_plan", role: "프로모션 계획", hint: "promotion_plan.xlsx / .csv" },
  { key: "product_master", role: "상품 마스터", hint: "product_master.xlsx / .csv" },
  { key: "inventory", role: "재고", hint: "inventory.xlsx / .csv" },
];
const { maxBytes: MAX_BYTES, allowedExtensions: ALLOWED } = getUploadLimits();
const SOURCE_REQUEST_ID = "__request__";
const state = {
  files: { promotion_plan: null, product_master: null, inventory: null },
  parsed: {
    promotion_plan: null,
    product_master: null,
    inventory: null,
  },
  result: null,
  fileIssues: {},
  highlightTargets: [],
  editorOpen: {},
  sourceCatalog: [],
  selectedSourceId: "upload",
  appliedChecklistItems: new Set(),
  dismissedChecklistItems: new Set(),
  pendingReview: new Set(),
  reviewItemsByKey: {},
  reviewResults: {},
  requestForm: {
    serviceName: "",
    details: "",
  },
  checklistEditors: {},
  auth: {
    signedIn: false,
    userId: null,
    displayName: null,
    sessionToken: null,
    provider: hasClerkMode() ? "clerk" : (isStubAuthAvailable() ? "stub" : "off"),
  },
  history: {
    granularity: "day",
    buckets: [],
    runs: [],
  },
};

/* ---------- extracted modules (PR1–3) ---------- */
const authUi = createAuthUi({
  state,
  $,
  toast,
  showView,
  renderDashboard: () => renderDashboard(),
  loadHistory: (granularity) => loadHistory(granularity),
});
const {
  authHeaders,
  initAuth,
  loadClerk,
  signIn,
  signOut,
} = authUi;

const issueView = createIssueView({
  el,
  state,
  SOURCE_LABELS,
  displayLabel,
  jumpToIssueLocation: (location, related) => jumpToIssueLocation(location, related),
  FIELDS,
});
const {
  renderIssueGroups,
  buildReviewStatusBadge,
} = issueView;

const reportView = createReportView({
  $,
  el,
  renderIssueGroups,
  renderChecklist: (report) => renderChecklist(report),
  renderFileEditors: () => renderFileEditors(),
  refreshEditedActions: () => refreshEditedActions(),
});
const { renderReport } = reportView;

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
      <input type="file" accept="${ALLOWED.join(",")}" />`;
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
    body.textContent = `지원하지 않는 형식: ${ext(file.name) || "확장자 없음"} · ${ALLOWED.join(" 또는 ")}만`;
    refreshRunBtn();
    return;
  }
  if (file.size > MAX_BYTES) {
    state.files[key] = null;
    zone.classList.add("error");
    body.className = "dz-body dz-err";
    body.textContent = `크기 초과: ${fmtSize(file.size)} · 최대 ${fmtSize(MAX_BYTES)}`;
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
    const res = await fetch("/api/preflight", {
      method: "POST",
      body: fd,
      headers: await authHeaders(),
    });
    if (!res.ok) {
      let detail = `검수 요청 실패 (${res.status})`;
      try {
        const j = await res.json();
        if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch (_) {}
      throw new Error(detail);
    }
    const report = await res.json();
    if (state.pendingReview.size > 0) {
      const diff = diffIssueKeys(state.pendingReview, report.issues, state.reviewItemsByKey);
      state.reviewResults = { ...diff.failed, ...diff.fixed };
      state.pendingReview = new Set(Object.keys(diff.failed));
    } else {
      state.reviewResults = {};
    }
    state.result = report;
    state.fileIssues = groupIssuesByFile(report.issues);
    renderReport(report);
    showView("view-result");
  } catch (err) {
    showView("view-upload");
    toast(err.message || "검수 중 오류가 발생했습니다.");
  }
}

/* ---------- reset ---------- */
function resetToUpload() {
  state.files = { promotion_plan: null, product_master: null, inventory: null };
  state.parsed = { promotion_plan: null, product_master: null, inventory: null };
  state.result = null;
  state.fileIssues = {};
  state.highlightTargets = [];
  state.editorOpen = {};
  state.appliedChecklistItems = new Set();
  state.dismissedChecklistItems = new Set();
  state.pendingReview = new Set();
  state.reviewItemsByKey = {};
  state.reviewResults = {};
  state.checklistEditors = {};
  buildDropzones();
  refreshRunBtn();
  refreshEditedActions();
  showView("view-upload");
}

/* ---------- init ---------- */
buildDropzones();
initTheme();
initAuth();
if (hasClerkMode()) {
  void loadClerk().catch((error) => {
    toast(error.message || "로그인 모듈을 불러오지 못했습니다.");
  });
}
void loadSources();
renderDashboard();
$("#run-btn").addEventListener("click", () => {
  void runPreflight();
});
$("#back-btn").addEventListener("click", resetToUpload);
$("#export-edited-top").addEventListener("click", exportAllEditedFiles);
$("#rerun-edited-top").addEventListener("click", () => {
  void rerunWithEditedFiles();
});
$("#auth-login")?.addEventListener("click", () => {
  void signIn();
});
$("#auth-logout")?.addEventListener("click", () => {
  void signOut();
});
$("#nav-dashboard")?.addEventListener("click", () => {
  showView("view-dashboard");
  void loadHistory(state.history.granularity);
});
$("#dashboard-back")?.addEventListener("click", () => showView("view-upload"));
bindWordmarkHome(document.querySelector(".wordmark"), () => showView("view-upload"));

async function buildParsedState(file) {
  if (isCsvFilename(file.name)) {
    try {
      const parsed = parseCsv(await file.text());
      const tooLarge = shouldDisableInlineEditing(parsed.rows.length);
      return {
        kind: "csv",
        editable: !tooLarge,
        headers: parsed.headers,
        rows: parsed.rows,
        pristine: {
          headers: [...parsed.headers],
          rows: parsed.rows.map((row) => [...row]),
        },
        originalRows: parsed.rows.map((row) => [...row]),
        edits: new Set(),
        structureDirty: false,
        addedRowIndexes: new Set(),
        addedColumnIndexes: new Set(),
        dirty: false,
        sourceName: file.name,
        sizeWarning: tooLarge ? buildLargeFileWarning(parsed.rows.length) : null,
      };
    } catch (error) {
      toast(error.message || "CSV 파싱에 실패했습니다.");
      return {
        kind: "csv",
        editable: false,
        headers: [],
        rows: [],
        pristine: { headers: [], rows: [] },
        originalRows: [],
        edits: new Set(),
        structureDirty: false,
        addedRowIndexes: new Set(),
        addedColumnIndexes: new Set(),
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
      pristine: { headers: [], rows: [] },
      originalRows: [],
      edits: new Set(),
      structureDirty: false,
      addedRowIndexes: new Set(),
      addedColumnIndexes: new Set(),
      dirty: false,
      sourceName: file.name,
    };
  }
  return null;
}



function renderDashboard() {
  const host = $("#history-dashboard");
  if (!host) {
    return;
  }
  host.innerHTML = "";
  if (!isSignedIn(state.auth)) {
    host.append(el("p", "caption mute", "로그인 후 일별·월별·연도별 검수 이력을 볼 수 있습니다."));
    return;
  }
  renderHistoryDashboard(host, state.history, displayLabel, loadHistory);
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
    const defaultOpen = shouldDefaultOpenEditor(field.key, host.children.length === 0);
    details.open = state.editorOpen[field.key] ?? defaultOpen;
    details.dataset.fileKey = field.key;
    details.addEventListener("toggle", () => {
      state.editorOpen[field.key] = details.open;
    });
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
      body.append(
        el("p", "caption mute", parsed.parseError || parsed.sizeWarning || "이 파일은 편집할 수 없습니다."),
      );
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
  wrap.dataset.fileKey = fileKey;
  const addRowButton = el("button", "btn btn-secondary", "행 추가");
  addRowButton.type = "button";
  addRowButton.addEventListener("click", () => addEditorRow(fileKey));
  wrap.append(addRowButton);

  const addColumnButton = el("button", "btn btn-secondary", "열 추가");
  addColumnButton.type = "button";
  addColumnButton.addEventListener("click", () => addEditorColumn(fileKey));
  wrap.append(addColumnButton);

  const exportButton = el("button", "btn btn-secondary", "수정본 CSV 내보내기");
  exportButton.dataset.fileAction = "export";
  exportButton.type = "button";
  exportButton.disabled = !parsed.dirty;
  exportButton.addEventListener("click", () => exportParsedFile(fileKey));
  wrap.append(exportButton);

  const revertButton = el("button", "btn btn-ghost", "원본으로 되돌리기");
  revertButton.type = "button";
  revertButton.disabled = !parsed.dirty;
  revertButton.addEventListener("click", () => revertEditorFile(fileKey));
  wrap.append(revertButton);

  const status = el(
    "span",
    "caption mute",
    parsed.dirty ? "편집한 셀을 포함해 CSV로 내보낼 수 있습니다." : "편집 후 수정본 내보내기가 활성화됩니다.",
  );
  status.dataset.fileAction = "status";
  wrap.append(status);
  return wrap;
}

function addEditorRow(fileKey) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv" || !parsed.editable) {
    return;
  }
  const rowIndex = parsed.rows.length;
  const nextRow = new Array(parsed.headers.length).fill("");
  parsed.rows.push(nextRow);
  parsed.originalRows.push(new Array(parsed.headers.length).fill(""));
  parsed.addedRowIndexes.add(rowIndex);
  parsed.structureDirty = true;
  parsed.dirty = true;
  renderFileEditors();
  refreshEditedActions();
}

function addEditorColumn(fileKey) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv" || !parsed.editable) {
    return;
  }
  const name = window.prompt("새 칼럼명을 입력해 주세요.", "")?.trim() ?? "";
  if (!name) {
    toast("칼럼명을 입력해야 합니다.");
    return;
  }
  if (parsed.headers.includes(name)) {
    toast("이미 있는 칼럼명입니다.");
    return;
  }
  const columnIndex = parsed.headers.length;
  parsed.headers.push(name);
  parsed.rows.forEach((row) => row.push(""));
  parsed.originalRows.forEach((row) => row.push(""));
  parsed.addedColumnIndexes.add(columnIndex);
  parsed.structureDirty = true;
  parsed.dirty = true;
  renderFileEditors();
  refreshEditedActions();
}

function revertEditorFile(fileKey) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv" || !parsed.dirty) {
    return;
  }
  revertParsed(parsed);
  renderFileEditors();
  refreshEditedActions();
}

function removeEditorRow(fileKey, rowIndex) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv" || !parsed.editable) {
    return;
  }
  deleteParsedRow(parsed, rowIndex);
  renderFileEditors();
  refreshEditedActions();
}

function removeEditorColumn(fileKey, columnIndex) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv" || !parsed.editable) {
    return;
  }
  deleteParsedColumn(parsed, columnIndex);
  renderFileEditors();
  refreshEditedActions();
}

function buildEditorHeadInner(labelText, deleteLabel, onDelete) {
  const inner = el("div", "file-editor-head-inner");
  inner.append(el("span", "file-editor-col-name", labelText));
  if (onDelete) {
    const removeButton = el("button", "file-editor-delete-btn", deleteLabel);
    removeButton.type = "button";
    removeButton.addEventListener("click", onDelete);
    inner.append(removeButton);
  }
  return inner;
}

function buildEditorTable(fileKey, parsed) {
  const scroller = el("div", "file-editor-table-wrap");
  const table = el("table", "file-editor-table");
  const thead = el("thead");
  const headRow = el("tr");
  const cornerHead = el("th", "file-editor-rowhead");
  cornerHead.append(buildEditorHeadInner("행"));
  headRow.append(cornerHead);
  parsed.headers.forEach((header, columnIndex) => {
    const th = el("th", "file-editor-column-head");
    th.append(
      buildEditorHeadInner(header, "열 삭제", () => removeEditorColumn(fileKey, columnIndex)),
    );
    headRow.append(th);
  });
  thead.append(headRow);
  table.append(thead);

  const tbody = el("tbody");
  parsed.rows.forEach((row, rowIndex) => {
    const tr = el("tr");
    const csvRowNumber = rowIndex + 2;
    tr.dataset.file = fileKey;
    tr.dataset.row = String(csvRowNumber);
    const rowHead = el("th", "file-editor-rowhead");
    rowHead.append(
      buildEditorHeadInner(String(csvRowNumber), "행 삭제", () =>
        removeEditorRow(fileKey, rowIndex),
      ),
    );
    tr.append(rowHead);
    row.forEach((value, columnIndex) => {
      const td = el("td");
      const input = el("input", "file-editor-input");
      input.value = value;
      input.dataset.file = fileKey;
      input.dataset.row = String(csvRowNumber);
      input.dataset.column = parsed.headers[columnIndex];
      input.addEventListener("input", () =>
        updateParsedCell(fileKey, rowIndex, columnIndex, input.value, td),
      );
      if (isEditedCell(parsed, rowIndex, columnIndex)) {
        td.classList.add("is-edited");
      }
      if (matchesHighlight(fileKey, csvRowNumber, parsed.headers[columnIndex])) {
        td.classList.add("is-highlighted");
      }
      td.append(input);
      tr.append(td);
    });
    if (matchesHighlight(fileKey, csvRowNumber, null)) {
      tr.classList.add("is-highlighted");
    }
    tbody.append(tr);
  });
  table.append(tbody);
  scroller.append(table);
  return scroller;
}

function updateParsedCell(fileKey, rowIndex, columnIndex, value, cell = null) {
  const parsed = state.parsed[fileKey];
  if (!parsed || parsed.kind !== "csv") {
    return;
  }
  applyParsedCellEdit(parsed, rowIndex, columnIndex, value);
  syncEditedCell(cell, parsed, rowIndex, columnIndex);
  syncEditorPresentation(fileKey, parsed);
  refreshEditedActions();
}

function isEditedCell(parsed, rowIndex, columnIndex) {
  return (
    parsed.edits.has(cellEditKey(rowIndex, columnIndex)) ||
    parsed.addedRowIndexes.has(rowIndex) ||
    parsed.addedColumnIndexes.has(columnIndex)
  );
}

function matchesHighlight(fileKey, row, column) {
  return state.highlightTargets.some(
    (target) =>
      target.file === fileKey &&
      target.row === row &&
      (column == null || target.column == null || target.column === column),
  );
}

function jumpToIssueLocation(location, related = []) {
  if (!location.file || !location.row) {
    return;
  }
  state.highlightTargets = buildHighlightTargets(location, related);
  state.highlightTargets.forEach((target) => {
    state.editorOpen[target.file] = true;
  });
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
  const items = mergeChecklistItems(report.checklist_items || []);
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
  const review = state.reviewResults[itemKey];
  if (review) {
    body.append(buildReviewStatusBadge(review));
  } else if (state.pendingReview.has(itemKey)) {
    body.append(el("span", "review-status status-pending", "수정안 검수 대기"));
  }
  li.append(body);

  const actions = el("div", "checklist-review-actions");
  const edit = el("button", "btn btn-secondary", "수정");
  edit.type = "button";
  edit.disabled = !canApplyChecklistItem(item);
  edit.addEventListener("click", () => toggleChecklistEditor(itemKey, item));
  actions.append(edit);

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
  if (state.checklistEditors[itemKey]?.open) {
    li.append(buildChecklistInlineEditor(itemKey, item));
  }
  return li;
}

function canApplyChecklistItem(item) {
  if (item.row == null || item.column == null) {
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

function saveChecklistEdit(itemKey, item) {
  const editorState = state.checklistEditors[itemKey];
  if (!canApplyChecklistItem(item) || item.row == null || item.column == null || !editorState) {
    return;
  }
  const parsed = state.parsed[item.file];
  const rowIndex = item.row - 2;
  const columnIndex = parsed.headers.indexOf(item.column);
  const nextValue = sanitizeChecklistCellValue(editorState.value, item.column);
  updateParsedCell(item.file, rowIndex, columnIndex, nextValue);
  state.appliedChecklistItems.add(checklistItemKey(item));
  state.pendingReview.add(itemKey);
  state.reviewItemsByKey[itemKey] = item;
  delete state.reviewResults[itemKey];
  state.checklistEditors[itemKey] = { open: false, value: nextValue };
  renderChecklist(state.result);
}

function shouldDefaultOpenEditor(fileKey, isFirst) {
  if (state.highlightTargets.some((target) => target.file === fileKey)) {
    return true;
  }
  return isFirst;
}

function syncEditedCell(cell, parsed, rowIndex, columnIndex) {
  if (!cell) {
    return;
  }
  cell.classList.toggle("is-edited", isEditedCell(parsed, rowIndex, columnIndex));
}

function syncEditorPresentation(fileKey, parsed) {
  const details = document.querySelector(`.file-editor[data-file-key="${fileKey}"]`);
  if (!details) {
    return;
  }
  let badge = details.querySelector(".file-editor-badge.dirty, .file-editor-badge.editable");
  if (!badge && parsed.editable) {
    badge = el("span", "file-editor-badge editable", "CSV 편집 가능");
    details.querySelector(".file-editor-summary")?.append(badge);
  }
  if (badge) {
    badge.className = `file-editor-badge ${parsed.dirty ? "dirty" : "editable"}`;
    badge.textContent = parsed.dirty ? "수정됨" : "CSV 편집 가능";
  }
  const exportButton = details.querySelector('[data-file-action="export"]');
  if (exportButton) {
    exportButton.disabled = !parsed.dirty;
  }
  const status = details.querySelector('[data-file-action="status"]');
  if (status) {
    status.textContent = parsed.dirty
      ? "편집한 셀을 포함해 CSV로 내보낼 수 있습니다."
      : "편집 후 수정본 내보내기가 활성화됩니다.";
  }
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
    const response = await fetch("/api/preflight/sources", { headers: await authHeaders() });
    if (!response.ok) {
      return;
    }
    state.sourceCatalog = await response.json();
    renderSourcePicker();
  } catch (_) {}
}

async function loadHistory(granularity = state.history.granularity) {
  state.history.granularity = normalizeGranularity(granularity);
  if (!isSignedIn(state.auth)) {
    renderDashboard();
    return;
  }
  try {
    const [summaryResponse, runsResponse] = await Promise.all([
      fetch(buildHistoryUrl(state.history.granularity), {
        headers: await authHeaders(),
      }),
      fetch(buildHistoryRunsUrl(), {
        headers: await authHeaders(),
      }),
    ]);
    if (summaryResponse.status === 401 || runsResponse.status === 401) {
      await signOut();
      toast("대시보드는 로그인 후 사용할 수 있습니다.");
      return;
    }
    if (!summaryResponse.ok) {
      throw new Error(`대시보드 조회 실패 (${summaryResponse.status})`);
    }
    if (!runsResponse.ok) {
      throw new Error(`실행 로그 조회 실패 (${runsResponse.status})`);
    }
    const [buckets, runs] = await Promise.all([
      summaryResponse.json(),
      runsResponse.json(),
    ]);
    state.history.buckets = buckets;
    state.history.runs = runs;
    renderDashboard();
  } catch (error) {
    toast(error.message || "대시보드를 불러오지 못했습니다.");
  }
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
    prependSourceIcon(button, source.id);
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
  const requestButton = el("button", "source-chip source-chip-request", "+ 서비스 추가 요청");
  requestButton.type = "button";
  requestButton.setAttribute("aria-pressed", String(state.selectedSourceId === SOURCE_REQUEST_ID));
  requestButton.classList.toggle("active", state.selectedSourceId === SOURCE_REQUEST_ID);
  requestButton.addEventListener("click", () => {
    state.selectedSourceId = SOURCE_REQUEST_ID;
    renderSourcePicker();
  });
  prependSourceIcon(requestButton, SOURCE_REQUEST_ID);
  chips.append(requestButton);

  if (state.selectedSourceId === SOURCE_REQUEST_ID) {
    panel.append(renderSourceRequestForm());
  }
  host.append(chips);
  host.append(panel);

  const dropzones = $("#dropzones");
  if (dropzones) {
    dropzones.classList.toggle("hidden", state.selectedSourceId !== "upload");
  }
}

function renderSourceRequestForm() {
  const wrap = el("form", "source-request-form");
  wrap.addEventListener("submit", (event) => {
    event.preventDefault();
    submitSourceRequest();
  });
  wrap.append(el("div", "source-preview-title", "서비스 추가 요청"));
  wrap.append(el("div", "source-preview-body", "필요한 서비스와 원하는 연결 기능을 남기면 GitHub 이슈 작성 화면으로 연결합니다."));

  const serviceInput = el("input", "source-request-input");
  serviceInput.type = "text";
  serviceInput.placeholder = "서비스명";
  serviceInput.value = state.requestForm.serviceName;
  serviceInput.addEventListener("input", () => {
    state.requestForm.serviceName = serviceInput.value;
  });
  wrap.append(serviceInput);

  const detailInput = el("textarea", "source-request-textarea");
  detailInput.placeholder = "원하는 데이터 소스나 기능을 적어주세요.";
  detailInput.value = state.requestForm.details;
  detailInput.addEventListener("input", () => {
    state.requestForm.details = detailInput.value;
  });
  wrap.append(detailInput);

  const submit = el("button", "btn btn-secondary", "요청 보내기");
  submit.type = "submit";
  wrap.append(submit);
  return wrap;
}

function submitSourceRequest() {
  if (!state.requestForm.serviceName.trim()) {
    toast("서비스명을 입력해 주세요.");
    return;
  }
  const url = buildServiceRequestUrl(
    state.requestForm.serviceName.trim(),
    state.requestForm.details.trim(),
  );
  window.open(url, "_blank", "noopener,noreferrer");
  toast("GitHub 이슈 작성 화면을 열었습니다.");
}

function toggleChecklistEditor(itemKey, item) {
  const nextOpen = !state.checklistEditors[itemKey]?.open;
  state.checklistEditors[itemKey] = {
    open: nextOpen,
    value: state.checklistEditors[itemKey]?.value ?? item.suggested ?? item.current ?? "",
  };
  renderChecklist(state.result);
}

function buildChecklistInlineEditor(itemKey, item) {
  const wrap = el("div", "checklist-inline-editor");
  const editorState = state.checklistEditors[itemKey];
  const input = el("input", "checklist-inline-input");
  input.type = "text";
  input.value = editorState?.value ?? item.suggested ?? item.current ?? "";
  input.disabled = !canApplyChecklistItem(item);
  input.addEventListener("input", () => {
    state.checklistEditors[itemKey] = {
      open: true,
      value: input.value,
    };
  });
  wrap.append(input);
  if (!canApplyChecklistItem(item)) {
    wrap.append(el("span", "caption mute", "이 파일은 인라인 수정으로 반영할 수 없습니다."));
    return wrap;
  }
  const save = el("button", "btn btn-secondary", "저장");
  save.type = "button";
  save.addEventListener("click", () => saveChecklistEdit(itemKey, item));
  wrap.append(save);
  const cancel = el("button", "btn btn-ghost", "취소");
  cancel.type = "button";
  cancel.addEventListener("click", () => {
    state.checklistEditors[itemKey] = { open: false, value: input.value };
    renderChecklist(state.result);
  });
  wrap.append(cancel);
  return wrap;
}


function mergeChecklistItems(currentItems) {
  const merged = [...currentItems];
  Object.entries(state.reviewResults).forEach(([key, result]) => {
    if (result.status !== "fixed" || !result.item) {
      return;
    }
    if (merged.some((item) => checklistItemKey(item) === key)) {
      return;
    }
    merged.push(result.item);
  });
  return merged;
}

function prependSourceIcon(button, sourceId) {
  const icon = el("span", "source-chip-icon");
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = SOURCE_ICONS[sourceId] || SOURCE_ICONS.fallback;
  button.prepend(icon);
}

const SOURCE_ICONS = {
  upload: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/></svg>',
  notion: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9v7"/><path d="m9 9 6 7"/><path d="M15 9v7"/></svg>',
  google_sheets: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M10 12h5M10 16h5"/></svg>',
  csv_url: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 14 8 16a3 3 0 1 1-4-4l2-2"/><path d="m14 10 2-2a3 3 0 1 1 4 4l-2 2"/><path d="m9 15 6-6"/></svg>',
  [SOURCE_REQUEST_ID]: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>',
  fallback: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8"/></svg>',
};
