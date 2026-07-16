/**
 * Client-side report export: Markdown, PDF (print), JSON, CSV.
 * Uses the same plain/technical narrative selection as the result UI.
 */

function slugify(text) {
  return String(text || "report")
    .replace(/[^\w가-힣\-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48) || "report";
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
}

export function reportBasename(payload) {
  const name = payload?.summary?.product_name || "rop";
  return `rop-report-${slugify(name)}-${stamp()}`;
}

function pickNarrative(payload, expert) {
  const comparison =
    expert && payload.comparison_technical
      ? payload.comparison_technical
      : payload.comparison;
  const evidence =
    expert && payload.evidence_technical?.length
      ? payload.evidence_technical
      : payload.evidence;
  const recommendation =
    expert && payload.recommendation_technical
      ? payload.recommendation_technical
      : payload.recommendation;
  return { comparison, evidence, recommendation };
}

function fmt(n, digits = 1) {
  return Number(n).toLocaleString("ko-KR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}

export function buildMarkdown(payload, { expert = false } = {}) {
  const { comparison, evidence, recommendation } = pickNarrative(payload, expert);
  const s = payload.summary;
  const mode = expert ? "전문 해설" : "쉬운 설명";
  const lines = [
    `# 매장 특화 ROP 리포트`,
    ``,
    `> 생성: ${new Date().toLocaleString("ko-KR")} · 모드: ${mode}`,
    ``,
    `## 추천 결과`,
    ``,
    recommendation,
    ``,
  ];

  if (payload.guidance?.length) {
    lines.push(`## 입력 안내`, ``);
    for (const g of payload.guidance) lines.push(`- ${g}`);
    lines.push(``);
  }

  lines.push(
    `## 핵심 수치`,
    ``,
    `| 항목 | 값 |`,
    `| --- | --- |`,
    `| 발주 시점 재고 (ROP) | ${fmt(payload.calc.recommended_rop, 0)} 개 |`,
    `| 여유 재고 (SS) | ${fmt(payload.calc.store_safety_stock, 1)} 개 |`,
    `| 1회 발주량 (Q) | ${fmt(payload.calc.suggested_order_qty, 1)} 개 |`,
    `| 발주 요일 · 주기 | ${payload.calc.order_days_label} · ${fmt(payload.calc.order_cycle_days, 1)} 일 |`,
    `| 배송 리드타임 | ${fmt(payload.calc.standard_lead_time_days, 1)} 일 (고정) |`,
    ``,
    `## 매장 · 품목 요약`,
    ``,
    `| 항목 | 내용 |`,
    `| --- | --- |`,
    `| 분석 품목 | ${s.product_name} |`,
    `| 유형 / 규모 | ${s.store_type_label} / ${s.store_size_label} |`,
    `| 객단가 | ${s.avg_ticket_label} |`,
    `| 입지 / 접근성 | ${s.location_dong} / ${s.accessibility_label} |`,
  );
  if (s.use_precise_location && s.store_address) {
    lines.push(`| 상세 주소 | ${s.store_address} |`);
  }
  lines.push(
    `| 상권 | ${s.trade_area_label} |`,
    `| 서비스 레벨 | ${s.service_level_label || "-"} |`,
    `| 발주 패턴 | ${s.order_day_pattern_label || "-"} |`,
    ``,
    `## 비교 표`,
    ``,
    `| 구분 | 일반/표준 | 이 매장 추천 | 변동 |`,
    `| --- | ---: | ---: | --- |`,
  );
  for (const r of comparison.rows) {
    lines.push(
      `| ${r.metric} | ${fmt(r.standard_value)} ${r.unit} | ${fmt(r.recommended_value)} ${r.unit} | ${r.delta_label} |`,
    );
  }
  lines.push(``, comparison.rop_guidance, ``, `## 근거`, ``);
  for (const block of evidence) {
    lines.push(`### ${block.title}`, ``, `*${block.calc_summary}*`, ``);
    for (const p of block.points) lines.push(`- ${p}`);
    lines.push(``);
  }
  lines.push(
    `---`,
    ``,
    `*MD Preflight ROP · template ${payload.template_id} v${payload.template_version}*`,
    ``,
  );
  return lines.join("\n");
}

export function buildComparisonCsv(payload, { expert = false } = {}) {
  const { comparison } = pickNarrative(payload, expert);
  const esc = (v) => {
    const s = String(v ?? "");
    if (/[",\n]/.test(s)) return `"${s.replaceAll('"', '""')}"`;
    return s;
  };
  const rows = [
    ["metric", "standard", "recommended", "delta", "unit", "delta_label"].map(esc).join(","),
  ];
  for (const r of comparison.rows) {
    rows.push(
      [
        r.metric,
        r.standard_value,
        r.recommended_value,
        r.delta,
        r.unit,
        r.delta_label,
      ]
        .map(esc)
        .join(","),
    );
  }
  // UTF-8 BOM for Excel
  return `\uFEFF${rows.join("\n")}\n`;
}

export function buildPrintableHtml(payload, { expert = false } = {}) {
  const { comparison, evidence, recommendation } = pickNarrative(payload, expert);
  const s = payload.summary;
  const mode = expert ? "전문 해설" : "쉬운 설명";
  const guide =
    payload.guidance?.length
      ? `<div class="box"><strong>입력 안내</strong><ul>${payload.guidance
          .map((g) => `<li>${escape(g)}</li>`)
          .join("")}</ul></div>`
      : "";
  const cmpRows = comparison.rows
    .map(
      (r) => `<tr>
      <td>${escape(r.metric)}</td>
      <td>${escape(fmt(r.standard_value))} ${escape(r.unit)}</td>
      <td><strong>${escape(fmt(r.recommended_value))} ${escape(r.unit)}</strong></td>
      <td>${escape(r.delta_label)}</td>
    </tr>`,
    )
    .join("");
  const evidenceHtml = evidence
    .map(
      (b) => `<section class="ev">
      <h3>${escape(b.title)}</h3>
      <p class="calc">${escape(b.calc_summary)}</p>
      <ul>${b.points.map((p) => `<li>${escape(p)}</li>`).join("")}</ul>
    </section>`,
    )
    .join("");
  const address =
    s.use_precise_location && s.store_address
      ? `<tr><th>상세 주소</th><td colspan="3">${escape(s.store_address)}</td></tr>`
      : "";

  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>ROP 리포트 — ${escape(s.product_name)}</title>
<style>
  @page { margin: 16mm; }
  body { font-family: system-ui, -apple-system, "Noto Sans KR", sans-serif; color: #171717; line-height: 1.5; margin: 0; padding: 24px; font-size: 13px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 20px 0 8px; border-bottom: 1px solid #ebebeb; padding-bottom: 4px; }
  h3 { font-size: 13px; margin: 0 0 4px; }
  .meta { color: #888; font-size: 12px; margin-bottom: 16px; }
  .verdict { background: #d6f0dd; border-left: 3px solid #0a7d33; padding: 12px 14px; border-radius: 6px; font-weight: 600; margin: 12px 0; }
  .box { background: #fafafa; border: 1px solid #ebebeb; border-radius: 6px; padding: 10px 12px; margin: 10px 0; }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0; }
  .stat { background: #fafafa; border: 1px solid #ebebeb; border-radius: 6px; padding: 10px; }
  .stat b { display: block; font-size: 18px; letter-spacing: -0.5px; }
  .stat span { color: #888; font-size: 11px; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0; }
  th, td { border: 1px solid #ebebeb; padding: 8px 10px; text-align: left; vertical-align: top; }
  th { background: #f5f5f5; font-weight: 500; color: #4d4d4d; font-size: 12px; }
  .sum th { width: 18%; background: #fafafa; }
  .ev { break-inside: avoid; margin: 10px 0; padding: 10px 12px; border: 1px solid #ebebeb; border-radius: 6px; }
  .calc { color: #0070f3; margin: 0 0 6px; font-size: 12px; }
  ul { margin: 0; padding-left: 1.1rem; }
  .guide { color: #4d4d4d; margin-top: 8px; }
  .foot { margin-top: 24px; color: #888; font-size: 11px; }
  @media print {
    body { padding: 0; }
    .no-print { display: none !important; }
  }
</style>
</head>
<body>
  <div class="no-print" style="margin-bottom:16px;display:flex;gap:8px;align-items:center;">
    <button onclick="window.print()" style="height:36px;padding:0 14px;border-radius:6px;border:0;background:#0070f3;color:#fff;font-weight:500;cursor:pointer;">PDF로 저장 / 인쇄</button>
    <span style="color:#888;font-size:12px;">브라우저 인쇄 대화상자에서 「PDF로 저장」을 선택하세요.</span>
  </div>
  <h1>매장 특화 ROP 리포트</h1>
  <p class="meta">${escape(new Date().toLocaleString("ko-KR"))} · ${escape(mode)} · ${escape(s.product_name)}</p>
  <div class="verdict">${escape(recommendation)}</div>
  ${guide}
  <div class="stats">
    <div class="stat"><b>${escape(fmt(payload.calc.recommended_rop, 0))}</b><span>발주 시점 재고 (개)</span></div>
    <div class="stat"><b>${escape(fmt(payload.calc.store_safety_stock, 1))}</b><span>여유 재고 (개)</span></div>
    <div class="stat"><b>${escape(fmt(payload.calc.suggested_order_qty, 1))}</b><span>1회 발주량 (개)</span></div>
    <div class="stat"><b>${escape(payload.calc.order_days_label || "—")}</b><span>발주 요일 · ${escape(fmt(payload.calc.order_cycle_days, 1))}일</span></div>
  </div>
  <h2>매장 · 품목 요약</h2>
  <table class="sum">
    <tr><th>분석 품목</th><td>${escape(s.product_name)}</td><th>유형 / 규모</th><td>${escape(s.store_type_label)} / ${escape(s.store_size_label)}</td></tr>
    <tr><th>객단가</th><td>${escape(s.avg_ticket_label)}</td><th>입지 / 접근성</th><td>${escape(s.location_dong)} / ${escape(s.accessibility_label)}</td></tr>
    ${address}
    <tr><th>상권</th><td>${escape(s.trade_area_label)}</td><th>서비스 레벨</th><td>${escape(s.service_level_label || "-")}</td></tr>
    <tr><th>발주 패턴</th><td colspan="3">${escape(s.order_day_pattern_label || "-")}</td></tr>
  </table>
  <h2>비교 표</h2>
  <table>
    <thead><tr><th>구분</th><th>일반/표준</th><th>이 매장 추천</th><th>변동</th></tr></thead>
    <tbody>${cmpRows}</tbody>
  </table>
  <p class="guide">${escape(comparison.rop_guidance)}</p>
  <h2>근거</h2>
  ${evidenceHtml}
  <p class="foot">MD Preflight ROP · ${escape(payload.template_id)} v${escape(payload.template_version)}</p>
</body>
</html>`;
}

function escape(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function downloadText(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/**
 * PDF export without window.open (works even when site popups are restricted).
 * Writes a temporary hidden iframe and opens the browser print dialog
 * (user chooses "Save as PDF").
 */
export function openPrintablePdf(payload, { expert = false } = {}) {
  const html = buildPrintableHtml(payload, { expert });
  // Drop the on-page "print" chrome — print dialog is the primary path.
  const printHtml = html
    .replace(/<div class="no-print"[\s\S]*?<\/div>/, "")
    .replace(
      "</head>",
      "<style>@media print{body{padding:12mm}}</style></head>",
    );

  // Remove any previous export iframe
  document.getElementById("rop-print-frame")?.remove();

  const iframe = document.createElement("iframe");
  iframe.id = "rop-print-frame";
  iframe.setAttribute("aria-hidden", "true");
  iframe.setAttribute("title", "ROP report print");
  // Off-screen but not zero-size: some engines skip print on 0×0 frames.
  Object.assign(iframe.style, {
    position: "fixed",
    right: "0",
    bottom: "0",
    width: "1px",
    height: "1px",
    opacity: "0",
    border: "0",
    pointerEvents: "none",
  });
  document.body.appendChild(iframe);

  const win = iframe.contentWindow;
  const doc = win?.document;
  if (!win || !doc) {
    iframe.remove();
    // Last resort: download HTML the user can open and print.
    downloadText(
      `${reportBasename(payload)}.html`,
      printHtml,
      "text/html;charset=utf-8",
    );
    return;
  }

  doc.open();
  doc.write(printHtml);
  doc.close();

  const cleanup = () => {
    setTimeout(() => {
      iframe.remove();
    }, 1500);
  };

  const fallbackHtml = () => {
    downloadText(
      `${reportBasename(payload)}.html`,
      printHtml,
      "text/html;charset=utf-8",
    );
    // User-visible notice: deferred print can no-op when gesture is lost.
    window.alert(
      "인쇄 창을 열 수 없어 HTML 파일로 저장했습니다. 받은 파일을 연 뒤 인쇄(PDF 저장)해 주세요.",
    );
  };

  const triggerPrint = () => {
    try {
      win.focus();
      win.print();
    } catch {
      fallbackHtml();
    } finally {
      cleanup();
    }
  };

  // Immediate print first (best chance to keep the user-gesture stack).
  // load + short timeout remain for engines that are not ready right after doc.write.
  let printed = false;
  const once = () => {
    if (printed) return;
    printed = true;
    triggerPrint();
  };
  once();
  iframe.addEventListener("load", once, { once: true });
  setTimeout(once, 250);
}

/**
 * @param {"markdown"|"pdf"|"json"|"csv"} format
 * @param {object} payload
 * @param {{ expert?: boolean }} options
 */
export function exportReport(format, payload, options = {}) {
  if (!payload) throw new Error("내보낼 리포트가 없습니다.");
  const expert = Boolean(options.expert);
  const base = reportBasename(payload);

  if (format === "markdown") {
    downloadText(`${base}.md`, buildMarkdown(payload, { expert }), "text/markdown;charset=utf-8");
    return;
  }
  if (format === "csv") {
    downloadText(
      `${base}-comparison.csv`,
      buildComparisonCsv(payload, { expert }),
      "text/csv;charset=utf-8",
    );
    return;
  }
  if (format === "json") {
    const body = JSON.stringify(payload, null, 2);
    downloadText(`${base}.json`, body, "application/json;charset=utf-8");
    return;
  }
  if (format === "pdf") {
    openPrintablePdf(payload, { expert });
    return;
  }
  throw new Error(`지원하지 않는 형식: ${format}`);
}
