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
import { createRouter, ROUTES } from "./router.mjs";
import { formatPreflightError } from "./error_format.mjs";

const FIELDS = [
  {
    key: "promotion_plan",
    role: "프로모션 계획",
    hint: "csv / xlsx · 행사코드·행사가 별칭 가능",
    blurb: "기간 · 행사가 · 증정 조건",
  },
  {
    key: "product_master",
    role: "상품 마스터",
    hint: "csv / xlsx · SKU·품명·정상가·원가",
    blurb: "정상가 · 원가 · 상품명",
  },
  {
    key: "inventory",
    role: "재고",
    hint: "csv / xlsx · 재고수량·입고일·예상수요",
    blurb: "재고 · 입고 · 예상 수요",
  },
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
  catalog: null,
  /** @type {Array<{id: string, file: File, filename: string, sourceFilename: string, sheetName: string|null, role: string|null, suggestedRole: string|null, confidence: number, headers: string[], scores: object[]}>} */
  artifacts: [],
  detectBusy: false,
};

const FRAME_META = {
  promotion_plan: { label: "행사 라인", short: "promotion" },
  product_master: { label: "상품 기준가", short: "product" },
  inventory: { label: "공급·재고", short: "inventory" },
};

/* ---------- extracted modules (PR1–3) ---------- */
/** Late-bound so auth sign-out can return to hash home after router exists. */
let goHome = () => showView("view-upload");
const authUi = createAuthUi({
  state,
  $,
  toast,
  showView: (id) => {
    if (id === "view-upload") {
      goHome();
      return;
    }
    showView(id);
  },
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

const router = createRouter(showView, {
  hasResult: () => Boolean(state.result),
  onAfterRoute: (route) => {
    if (route === ROUTES.dashboard) {
      void loadHistory(state.history.granularity);
    }
    if (route === ROUTES.settings) {
      void loadCatalog().then(() => renderSettings());
    }
  },
});

/** Fallback when /catalog is unreachable (offline / early paint). */
const COLUMN_ALIAS_FALLBACK = [
  {
    source: "promotion_plan",
    label: "프로모션 계획",
    columns: [
      { canonical: "promotion_id", aliases: ["행사코드", "프로모션ID"] },
      { canonical: "product_code", aliases: ["상품코드", "품번", "SKU"] },
      { canonical: "promo_price", aliases: ["행사가", "할인가"] },
    ],
  },
  {
    source: "product_master",
    label: "상품 마스터",
    columns: [
      { canonical: "product_code", aliases: ["상품코드", "SKU"] },
      { canonical: "normal_price", aliases: ["정상가", "정가"] },
      { canonical: "cost", aliases: ["원가", "매입가"] },
    ],
  },
  {
    source: "inventory",
    label: "재고",
    columns: [
      { canonical: "stock_qty", aliases: ["재고", "재고수량"] },
      { canonical: "inbound_date", aliases: ["입고일", "입고예정일"] },
      { canonical: "expected_demand", aliases: ["예상수요"] },
    ],
  },
];

async function loadCatalog() {
  try {
    const res = await fetch("/api/preflight/catalog");
    if (!res.ok) throw new Error(`catalog ${res.status}`);
    state.catalog = await res.json();
  } catch (_) {
    if (!state.catalog) {
      state.catalog = {
        thresholds: { max_discount_rate: 0.7, min_margin_rate: 0.05 },
        sources: COLUMN_ALIAS_FALLBACK,
        rules: [],
        max_upload_bytes: MAX_BYTES,
        allowed_extensions: ALLOWED,
      };
    }
  }
  return state.catalog;
}

function pct(rate) {
  if (typeof rate !== "number" || Number.isNaN(rate)) return "—";
  const value = rate * 100;
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

function renderSettings() {
  const cfg = window.__MDP_CONFIG__ || {};
  const catalog = state.catalog;
  const authModeEl = $("#settings-auth-mode");
  const sessionEl = $("#settings-auth-session");
  const nameEl = $("#settings-auth-name");
  const maxBytesEl = $("#settings-max-bytes");
  const extEl = $("#settings-extensions");
  if (authModeEl) {
    authModeEl.textContent = cfg.authMode || state.auth.provider || "off";
  }
  if (sessionEl) {
    sessionEl.textContent = isSignedIn(state.auth) ? "로그인됨" : "비로그인";
  }
  if (nameEl) {
    nameEl.textContent =
      (isSignedIn(state.auth) && (state.auth.displayName || state.auth.userId)) || "—";
  }
  if (maxBytesEl) {
    const bytes = catalog?.max_upload_bytes ?? MAX_BYTES;
    maxBytesEl.textContent = fmtSize(bytes);
  }
  if (extEl) {
    const exts = catalog?.allowed_extensions ?? ALLOWED;
    extEl.textContent = (exts || []).join(", ") || "—";
  }

  const discEl = $("#settings-max-discount");
  const marginEl = $("#settings-min-margin");
  if (discEl) {
    discEl.textContent = pct(catalog?.thresholds?.max_discount_rate);
  }
  if (marginEl) {
    marginEl.textContent = pct(catalog?.thresholds?.min_margin_rate);
  }

  const rulesHost = $("#settings-rules");
  if (rulesHost) {
    rulesHost.replaceChildren();
    const rules = catalog?.rules || [];
    if (rules.length === 0) {
      rulesHost.append(el("p", "caption mute", "룰 목록을 불러오지 못했습니다. 잠시 후 다시 열어 주세요."));
    } else {
      const table = el("table", "settings-alias-table settings-rules-table");
      const thead = el("thead");
      const hr = el("tr");
      hr.append(el("th", null, "코드"));
      hr.append(el("th", null, "심각도"));
      hr.append(el("th", null, "설명"));
      thead.append(hr);
      table.append(thead);
      const tbody = el("tbody");
      rules.forEach((rule) => {
        const tr = el("tr");
        tr.append(el("td", "mono", rule.code));
        const sev = el("td", `sev-cell sev-${rule.severity || "info"}`, rule.severity || "—");
        tr.append(sev);
        tr.append(el("td", null, rule.description || "—"));
        tbody.append(tr);
      });
      table.append(tbody);
      rulesHost.append(table);
    }
  }

  const host = $("#settings-aliases");
  if (!host) return;
  host.replaceChildren();
  const sources = catalog?.sources?.length ? catalog.sources : COLUMN_ALIAS_FALLBACK;
  sources.forEach((group) => {
    const block = el("div", "settings-alias-group");
    block.append(el("h3", "settings-alias-source", group.label || group.source));
    const table = el("table", "settings-alias-table");
    const thead = el("thead");
    const hr = el("tr");
    hr.append(el("th", null, "정규 컬럼"));
    hr.append(el("th", null, "허용 별칭"));
    thead.append(hr);
    table.append(thead);
    const tbody = el("tbody");
    (group.columns || []).forEach((row) => {
      const tr = el("tr");
      tr.append(el("td", "mono", row.canonical));
      const aliasText = Array.isArray(row.aliases)
        ? row.aliases.join(", ")
        : (row.aliases || "—");
      tr.append(el("td", null, aliasText || "—"));
      tbody.append(tr);
    });
    table.append(tbody);
    block.append(table);
    host.append(block);
  });
}

/* ---------- upload adapter + role mapping (T57) ---------- */

function buildUploadAdapter() {
  const zone = $("#multi-dropzone");
  const input = $("#multi-file-input");
  if (!zone || !input) return;

  const takeFiles = (list) => {
    void addArtifacts(Array.from(list || []));
  };

  input.addEventListener("change", () => {
    takeFiles(input.files);
    input.value = "";
  });
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    takeFiles(e.dataTransfer?.files);
  });
  renderRoleMapper();
  renderFrameReadyBar();
}

function newArtifactId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `a-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function addArtifacts(fileList) {
  const accepted = [];
  for (const file of fileList) {
    if (!ALLOWED.includes(ext(file.name))) {
      toast(`지원하지 않는 형식: ${file.name}`);
      continue;
    }
    if (file.size > MAX_BYTES) {
      toast(`크기 초과: ${file.name} (최대 ${fmtSize(MAX_BYTES)})`);
      continue;
    }
    const dup = state.artifacts.some(
      (a) => a.filename === file.name && a.file.size === file.size,
    );
    if (dup) continue;
    accepted.push({
      id: newArtifactId(),
      file,
      filename: file.name,
      sourceFilename: file.name,
      sheetName: null,
      role: null,
      suggestedRole: null,
      confidence: 0,
      headers: [],
      scores: [],
    });
  }
  if (accepted.length === 0) {
    refreshRunBtn();
    return;
  }
  state.artifacts.push(...accepted);
  await runRoleDetection();
}

function uniqueSourceFiles() {
  const map = new Map();
  state.artifacts.forEach((artifact) => {
    const key = `${artifact.file.name}::${artifact.file.size}`;
    map.set(key, artifact.file);
  });
  return [...map.values()];
}

function priorRoleByKey(sourceFilename, sheetName) {
  const hit = state.artifacts.find(
    (a) =>
      (a.sourceFilename || a.file.name) === sourceFilename &&
      (a.sheetName || null) === (sheetName || null) &&
      a.role,
  );
  return hit?.role || null;
}

async function runRoleDetection() {
  if (state.artifacts.length === 0) {
    await syncFilesFromRoles();
    renderRoleMapper();
    renderFrameReadyBar();
    refreshRunBtn();
    return;
  }
  state.detectBusy = true;
  renderFrameReadyBar();
  try {
    const sources = uniqueSourceFiles();
    const fd = new FormData();
    sources.forEach((file) => {
      fd.append("files", file, file.name);
    });
    const res = await fetch("/api/preflight/detect-roles", {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      let detail = `역할 추정 실패 (${res.status})`;
      try {
        const j = await res.json();
        if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch (_) {}
      throw new Error(detail);
    }
    const payload = await res.json();
    const ordered = payload.artifacts || [];
    const fileByName = new Map(sources.map((file) => [file.name, file]));
    state.artifacts = ordered.map((hit) => {
      const sourceName = hit.source_filename || hit.filename;
      const sheetName = hit.sheet_name || null;
      const file = fileByName.get(sourceName) || sources[0];
      const kept = priorRoleByKey(sourceName, sheetName);
      return {
        id: hit.artifact_id || newArtifactId(),
        file,
        filename: hit.filename || sourceName,
        sourceFilename: sourceName,
        sheetName,
        role: kept || hit.assigned_role || hit.suggested_role || null,
        suggestedRole: hit.suggested_role || null,
        confidence: hit.confidence || 0,
        headers: hit.headers || [],
        scores: hit.scores || [],
      };
    });
    resolveRoleConflicts();
    const sheets = state.artifacts.filter((a) => a.sheetName).length;
    if (sheets > 0) {
      toast(`워크북 시트 ${sheets}개를 테이블로 분리했습니다.`, { durationMs: 3500 });
    }
  } catch (err) {
    toast(err.message || "역할 추정에 실패했습니다.");
  } finally {
    state.detectBusy = false;
    await syncFilesFromRoles();
    renderRoleMapper();
    renderFrameReadyBar();
    refreshRunBtn();
  }
}

function resolveRoleConflicts() {
  const seen = new Map();
  state.artifacts.forEach((artifact) => {
    if (!artifact.role) return;
    if (seen.has(artifact.role)) {
      // keep higher confidence
      const other = seen.get(artifact.role);
      if ((artifact.confidence || 0) > (other.confidence || 0)) {
        other.role = null;
        seen.set(artifact.role, artifact);
      } else {
        artifact.role = null;
      }
    } else {
      seen.set(artifact.role, artifact);
    }
  });
}

async function syncFilesFromRoles() {
  const next = { promotion_plan: null, product_master: null, inventory: null };
  const nextParsed = {
    promotion_plan: null,
    product_master: null,
    inventory: null,
  };
  for (const artifact of state.artifacts) {
    if (!artifact.role) continue;
    if (!Object.prototype.hasOwnProperty.call(next, artifact.role)) continue;
    if (next[artifact.role]) continue;
    next[artifact.role] = artifact.file;
    nextParsed[artifact.role] = await buildParsedState(artifact.file);
  }
  state.files = next;
  state.parsed = nextParsed;
  renderFileEditors();
}

function setArtifactRole(artifactId, role) {
  const artifact = state.artifacts.find((a) => a.id === artifactId);
  if (!artifact) return;
  const nextRole = role || null;
  if (nextRole) {
    state.artifacts.forEach((a) => {
      if (a.id !== artifactId && a.role === nextRole) a.role = null;
    });
  }
  artifact.role = nextRole;
  void syncFilesFromRoles().then(() => {
    renderRoleMapper();
    renderFrameReadyBar();
    refreshRunBtn();
  });
}

function removeArtifact(artifactId) {
  state.artifacts = state.artifacts.filter((a) => a.id !== artifactId);
  void syncFilesFromRoles().then(() => {
    renderRoleMapper();
    renderFrameReadyBar();
    refreshRunBtn();
  });
}

function renderFrameReadyBar() {
  const host = $("#frame-ready-bar");
  if (!host) return;
  host.replaceChildren();
  if (state.detectBusy) {
    host.append(el("span", "frame-chip frame-chip-busy", "역할 추정 중…"));
    return;
  }
  FIELDS.forEach((field) => {
    const assigned = state.artifacts.find((a) => a.role === field.key);
    const meta = FRAME_META[field.key] || { label: field.role };
    const chip = el(
      "span",
      `frame-chip ${assigned ? "frame-chip-ok" : "frame-chip-missing"}`,
      assigned
        ? `✓ ${meta.label}: ${assigned.filename}`
        : `○ ${meta.label} 미지정`,
    );
    host.append(chip);
  });
}

function renderRoleMapper() {
  const host = $("#role-mapper");
  if (!host) return;
  host.replaceChildren();
  if (state.artifacts.length === 0) {
    host.append(
      el(
        "p",
        "caption mute role-mapper-empty",
        "아직 업로드된 파일이 없습니다. dirty 또는 alias_ko 샘플 3종을 한 번에 올려 자동 매핑을 확인하세요.",
      ),
    );
    return;
  }

  const table = el("table", "role-map-table");
  const thead = el("thead");
  const hr = el("tr");
  ["파일", "추정", "역할 (프레임)", "신뢰도", ""].forEach((label) => {
    hr.append(el("th", null, label));
  });
  thead.append(hr);
  table.append(thead);
  const tbody = el("tbody");

  state.artifacts.forEach((artifact) => {
    const tr = el("tr");
    const nameCell = el("td");
    nameCell.append(el("div", null, artifact.filename));
    const metaBits = [];
    if (artifact.sheetName) metaBits.push(`시트 ${artifact.sheetName}`);
    if (artifact.headers?.length) metaBits.push(`헤더 ${artifact.headers.length}개`);
    else metaBits.push(fmtSize(artifact.file.size));
    nameCell.append(el("div", "caption mute", metaBits.join(" · ")));
    tr.append(nameCell);

    const suggestLabel = artifact.suggestedRole
      ? (FRAME_META[artifact.suggestedRole]?.label || artifact.suggestedRole)
      : "—";
    tr.append(el("td", "caption", suggestLabel));

    const select = el("select", "role-select");
    const emptyOpt = el("option", null, "역할 선택…");
    emptyOpt.value = "";
    select.append(emptyOpt);
    FIELDS.forEach((field) => {
      const opt = el("option", null, `${FRAME_META[field.key]?.label || field.role}`);
      opt.value = field.key;
      if (artifact.role === field.key) opt.selected = true;
      select.append(opt);
    });
    select.addEventListener("change", () => {
      setArtifactRole(artifact.id, select.value);
    });
    const selectTd = el("td");
    selectTd.append(select);
    tr.append(selectTd);

    const conf =
      typeof artifact.confidence === "number"
        ? `${Math.round(artifact.confidence * 100)}%`
        : "—";
    tr.append(el("td", "mono", conf));

    const removeBtn = el("button", "btn btn-ghost btn-sm", "제거");
    removeBtn.type = "button";
    removeBtn.addEventListener("click", () => removeArtifact(artifact.id));
    const actions = el("td");
    actions.append(removeBtn);
    tr.append(actions);

    tbody.append(tr);
  });
  table.append(tbody);
  host.append(table);

  const redetect = el("button", "btn btn-secondary btn-sm", "역할 다시 추정");
  redetect.type = "button";
  redetect.addEventListener("click", () => {
    state.artifacts.forEach((a) => {
      a.role = null;
    });
    void runRoleDetection();
  });
  const actionsRow = el("div", "role-mapper-actions");
  actionsRow.append(redetect);
  host.append(actionsRow);
}

function refreshRunBtn() {
  const ready = FIELDS.every((f) => state.files[f.key]);
  const btn = $("#run-btn");
  if (btn) btn.disabled = !ready || state.detectBusy;
}

/* ---------- run preflight ---------- */
function buildRoleMappingsPayload() {
  return FIELDS.map((field) => {
    const artifact = state.artifacts.find((a) => a.role === field.key);
    if (!artifact) return null;
    return {
      frame: field.key,
      source_filename: artifact.sourceFilename || artifact.file.name,
      sheet_name: artifact.sheetName || null,
      label: artifact.filename,
      confidence:
        typeof artifact.confidence === "number" ? artifact.confidence : null,
      suggested_role: artifact.suggestedRole || null,
      confirmed: true,
    };
  }).filter(Boolean);
}

async function runPreflight(filesOverride = null) {
  const fd = new FormData();
  FIELDS.forEach((f) => {
    const file = filesOverride?.[f.key] ?? state.files[f.key];
    fd.append(f.key, file);
  });
  fd.append("use_llm", $("#use-llm").checked ? "true" : "false");
  // T58: sheet selectors when a frame is backed by a workbook sheet
  const sheetFields = {
    promotion_plan: "promotion_sheet",
    product_master: "product_sheet",
    inventory: "inventory_sheet",
  };
  FIELDS.forEach((f) => {
    const artifact = state.artifacts.find((a) => a.role === f.key);
    if (artifact?.sheetName) {
      fd.append(sheetFields[f.key], artifact.sheetName);
    }
  });
  // T59: adapter role mapping audit trail
  const roleMappings = buildRoleMappingsPayload();
  if (roleMappings.length > 0) {
    fd.append("role_mappings", JSON.stringify(roleMappings));
  }

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
      const formatted = formatPreflightError(res.status, detail);
      const err = new Error(formatted.body);
      err.isColumnError = formatted.isColumnError;
      throw err;
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
    router.navigate(ROUTES.run);
  } catch (err) {
    router.navigate(ROUTES.home);
    toast(err.message || "검수 중 오류가 발생했습니다.", {
      multiline: Boolean(err.isColumnError || (err.message && err.message.includes("\n"))),
      durationMs: err.isColumnError ? 10000 : undefined,
    });
  }
}

/* ---------- reset ---------- */
function resetToUpload() {
  state.files = { promotion_plan: null, product_master: null, inventory: null };
  state.parsed = { promotion_plan: null, product_master: null, inventory: null };
  state.artifacts = [];
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
  renderRoleMapper();
  renderFrameReadyBar();
  refreshRunBtn();
  refreshEditedActions();
  router.navigate(ROUTES.home);
}

/* ---------- init ---------- */
buildUploadAdapter();
initTheme();
initAuth();
if (hasClerkMode()) {
  void loadClerk().catch((error) => {
    toast(error.message || "로그인 모듈을 불러오지 못했습니다.");
  });
}
void loadSources();
void loadCatalog().then(() => renderSettings());
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
document.querySelectorAll("[data-nav-route]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const route = btn.getAttribute("data-nav-route");
    if (!route) return;
    if (route === ROUTES.run && !state.result) {
      toast("먼저 검수를 실행하면 결과 화면으로 이동합니다.");
      router.navigate(ROUTES.home);
      return;
    }
    router.navigate(route);
  });
});
$("#dashboard-back")?.addEventListener("click", () => router.navigate(ROUTES.home));
bindWordmarkHome(document.querySelector(".wordmark"), () => router.navigate(ROUTES.home));
goHome = () => router.navigate(ROUTES.home);
router.start();

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

  const adapter = $("#upload-adapter");
  if (adapter) {
    adapter.classList.toggle("hidden", state.selectedSourceId !== "upload");
  }
  const dropzones = $("#dropzones");
  if (dropzones) {
    dropzones.classList.add("hidden");
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
