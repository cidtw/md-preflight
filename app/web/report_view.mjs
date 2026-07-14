/**
 * Preflight report summary panel (verdict, stats, AI, issues host).
 * Move-only extract from app.js.
 */

/**
 * @param {object} deps
 * @param {(sel: string) => Element|null} deps.$
 * @param {typeof import('./dom_util.mjs').el} deps.el
 * @param {(issues: object[], host: Element) => void} deps.renderIssueGroups
 * @param {(report: object) => void} deps.renderChecklist
 * @param {() => void} deps.renderFileEditors
 * @param {() => void} deps.refreshEditedActions
 */
export function createReportView(deps) {
  const {
    $,
    el,
    renderIssueGroups,
    renderChecklist,
    renderFileEditors,
    refreshEditedActions,
  } = deps;

  function renderFileSummaries(fileSummaries) {
    let host = $("#ai-file-summaries");
    if (!host) {
      host = el("div", "ai-file-summaries");
      host.id = "ai-file-summaries";
      $("#ai-summary")?.append(host);
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

  function renderReport(r) {
    const s = r.summary;

    // download link
    const dl = $("#download-md");
    if (dl) {
      dl.href = `/api/preflight/runs/${r.run_id}/report.md`;
    }

    // verdict
    const verdict = $("#verdict");
    const errCount = s.by_severity.error || 0;
    const warnCount = s.by_severity.warning || 0;
    if (verdict) {
      if (s.passed) {
        verdict.className = "verdict pass";
        verdict.innerHTML = `검수 통과 <span class="v-sub">차단 이슈 없음 · 상품 ${s.checked_rows}건 검수</span>`;
      } else {
        verdict.className = "verdict fail";
        verdict.innerHTML = `검수 실패 <span class="v-sub">error ${errCount}건 · warning ${warnCount}건 · 상품 ${s.checked_rows}건 검수</span>`;
      }
    }

    // stat tiles
    const stats = $("#stats");
    if (stats) {
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
    }

    // column mappings (T50)
    const mappings = Array.isArray(r.column_mappings) ? r.column_mappings : [];
    const mapCount = $("#mapping-count");
    if (mapCount) mapCount.textContent = String(mappings.length);
    const mapHost = $("#column-mappings");
    if (mapHost) {
      mapHost.innerHTML = "";
      if (mappings.length === 0) {
        mapHost.append(
          el("div", "empty-mapping", "별칭 변환 없음 — 업로드 헤더가 이미 정규 컬럼명입니다."),
        );
      } else {
        const table = el("table", "mapping-table");
        const thead = el("thead");
        const hr = el("tr");
        hr.append(el("th", null, "파일"));
        hr.append(el("th", null, "원본 헤더"));
        hr.append(el("th", null, "정규 키"));
        thead.append(hr);
        table.append(thead);
        const tbody = el("tbody");
        mappings.forEach((m) => {
          const tr = el("tr");
          tr.append(el("td", null, m.file || "—"));
          tr.append(el("td", "mono", m.original || "—"));
          tr.append(el("td", "mono mapping-canonical", m.canonical || "—"));
          tbody.append(tr);
        });
        table.append(tbody);
        mapHost.append(table);
      }
    }

    // issues
    const issueCount = $("#issue-count");
    if (issueCount) issueCount.textContent = r.issues.length;
    const list = $("#issues");
    if (list) {
      list.innerHTML = "";
      if (r.issues.length === 0) {
        list.classList.remove("issue-list");
        list.append(el("div", "empty-clean", "✓ 검수 통과 — 발견된 문제가 없습니다."));
      } else {
        list.classList.remove("issue-list");
        renderIssueGroups(r.issues, list);
      }
    }

    // ai summary + provenance
    const ai = $("#ai-summary");
    if (ai) {
      const isFallback = r.generated_by !== "llm";
      ai.className = `ai-panel has-badge ${isFallback ? "is-fallback" : "is-llm"}`;
      ai.innerHTML = "";
      const badge = el(
        "span",
        `prov-badge ${r.generated_by === "llm" ? "llm" : "fallback"}`,
        r.generated_by,
      );
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
    }

    renderFileSummaries(r.file_summaries || []);

    // checklist + editors
    renderChecklist(r);
    renderFileEditors();
    refreshEditedActions();
  }

  return { renderReport, renderFileSummaries };
}
