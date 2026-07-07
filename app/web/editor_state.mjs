export function applyParsedCellEdit(parsed, rowIndex, columnIndex, value) {
  parsed.rows[rowIndex][columnIndex] = value;
  const key = cellEditKey(rowIndex, columnIndex);
  if (parsed.originalRows[rowIndex][columnIndex] === value) {
    parsed.edits.delete(key);
  } else {
    parsed.edits.add(key);
  }
  parsed.dirty = parsed.edits.size > 0 || parsed.structureDirty;
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

export function sanitizeChecklistCellValue(value, column) {
  if (!column) {
    return value;
  }
  const escapedColumn = column.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return value.replace(new RegExp(`^\\s*${escapedColumn}\\s*=\\s*`), "");
}

export function deleteParsedRow(parsed, rowIndex) {
  parsed.rows.splice(rowIndex, 1);
  parsed.originalRows.splice(rowIndex, 1);
  parsed.edits = rebuildEditKeys(parsed.edits, {
    deletedRowIndex: rowIndex,
    deletedColumnIndex: null,
  });
  parsed.addedRowIndexes = rebuildRowIndexes(parsed.addedRowIndexes, rowIndex);
  parsed.structureDirty = true;
  parsed.dirty = parsed.edits.size > 0 || parsed.structureDirty;
}

export function deleteParsedColumn(parsed, columnIndex) {
  parsed.headers.splice(columnIndex, 1);
  parsed.rows.forEach((row) => row.splice(columnIndex, 1));
  parsed.originalRows.forEach((row) => row.splice(columnIndex, 1));
  parsed.edits = rebuildEditKeys(parsed.edits, {
    deletedRowIndex: null,
    deletedColumnIndex: columnIndex,
  });
  parsed.addedColumnIndexes = rebuildColumnIndexes(parsed.addedColumnIndexes, columnIndex);
  parsed.structureDirty = true;
  parsed.dirty = parsed.edits.size > 0 || parsed.structureDirty;
}

export function revertParsed(parsed) {
  parsed.headers = [...parsed.pristine.headers];
  parsed.rows = parsed.pristine.rows.map((row) => [...row]);
  parsed.originalRows = parsed.pristine.rows.map((row) => [...row]);
  parsed.edits = new Set();
  parsed.addedRowIndexes = new Set();
  parsed.addedColumnIndexes = new Set();
  parsed.structureDirty = false;
  parsed.dirty = false;
}

function rebuildEditKeys(edits, { deletedRowIndex, deletedColumnIndex }) {
  const rebuilt = new Set();
  edits.forEach((key) => {
    const [rowText, columnText] = key.split(",");
    let rowIndex = Number(rowText);
    let columnIndex = Number(columnText);
    if (deletedRowIndex != null) {
      if (rowIndex === deletedRowIndex) {
        return;
      }
      if (rowIndex > deletedRowIndex) {
        rowIndex -= 1;
      }
    }
    if (deletedColumnIndex != null) {
      if (columnIndex === deletedColumnIndex) {
        return;
      }
      if (columnIndex > deletedColumnIndex) {
        columnIndex -= 1;
      }
    }
    rebuilt.add(cellEditKey(rowIndex, columnIndex));
  });
  return rebuilt;
}

function rebuildRowIndexes(indexes, deletedRowIndex) {
  const rebuilt = new Set();
  indexes.forEach((rowIndex) => {
    if (rowIndex === deletedRowIndex) {
      return;
    }
    rebuilt.add(rowIndex > deletedRowIndex ? rowIndex - 1 : rowIndex);
  });
  return rebuilt;
}

function rebuildColumnIndexes(indexes, deletedColumnIndex) {
  const rebuilt = new Set();
  indexes.forEach((columnIndex) => {
    if (columnIndex === deletedColumnIndex) {
      return;
    }
    rebuilt.add(columnIndex > deletedColumnIndex ? columnIndex - 1 : columnIndex);
  });
  return rebuilt;
}
