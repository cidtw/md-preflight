/**
 * Turn API error detail into operator-friendly Korean copy (T52).
 * Keeps raw detail when structure is unknown.
 */

/**
 * @param {number} status
 * @param {unknown} detail
 * @returns {{ title: string, body: string, isColumnError: boolean }}
 */
export function formatPreflightError(status, detail) {
  const raw =
    typeof detail === "string"
      ? detail
      : detail == null
        ? `검수 요청 실패 (${status})`
        : JSON.stringify(detail);

  // Greedy column list until '(' — non-greedy + optional group wrongly matched "i" only.
  const missing = raw.match(
    /Missing columns in ([a-z_]+):\s*([^(]+?)(?:\s*\(similar headers:\s*([^)]+)\))\s*$/i,
  ) || raw.match(/Missing columns in ([a-z_]+):\s*(.+)$/i);
  if (missing) {
    const source = missing[1].trim();
    const cols = missing[2]
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const hints = (missing[3] || "")
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean);

    const sourceLabel = {
      promotion_plan: "프로모션 계획",
      product_master: "상품 마스터",
      inventory: "재고",
    }[source] || source;

    const lines = [
      `[${sourceLabel}] 필수 컬럼이 없습니다.`,
      `부족한 컬럼: ${cols.map((c) => `\`${c}\``).join(", ")}`,
    ];
    if (hints.length) {
      lines.push("힌트:");
      hints.forEach((h) => lines.push(`  · ${h}`));
    } else {
      lines.push("허용 별칭은 설정 화면의 컬럼 표에서 확인할 수 있습니다.");
    }
    lines.push("설정(#/settings) → 컬럼 별칭 표를 참고하세요.");
    return {
      title: "컬럼 오류",
      body: lines.join("\n"),
      isColumnError: true,
    };
  }

  if (status === 413) {
    return {
      title: "파일 크기",
      body: raw || "업로드 용량 한도를 초과했습니다.",
      isColumnError: false,
    };
  }
  if (status === 400) {
    return {
      title: "파일 형식",
      body: raw || "지원하지 않는 확장자입니다. csv / xlsx 만 가능합니다.",
      isColumnError: false,
    };
  }

  return {
    title: "오류",
    body: raw || `검수 요청 실패 (${status})`,
    isColumnError: false,
  };
}
