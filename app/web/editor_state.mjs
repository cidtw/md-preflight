export function applyParsedCellEdit(parsed, rowIndex, columnIndex, value) {
  parsed.rows[rowIndex][columnIndex] = value;
  const key = cellEditKey(rowIndex, columnIndex);
  if (parsed.originalRows[rowIndex][columnIndex] === value) {
    parsed.edits.delete(key);
  } else {
    parsed.edits.add(key);
  }
  parsed.dirty = parsed.edits.size > 0;
}

export function buildHighlightTargets(primary, related = []) {
  const targets = [];
  const seen = new Set();
  [primary, ...related].forEach((location) => {
    if (!location?.file) {
      return;
    }
    const key = [location.file, location.row ?? "-", location.column ?? "-"].join(":");
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    targets.push({
      file: location.file,
      row: location.row ?? null,
      column: location.column ?? null,
    });
  });
  return targets;
}

export function cellEditKey(rowIndex, columnIndex) {
  return `${rowIndex},${columnIndex}`;
}
