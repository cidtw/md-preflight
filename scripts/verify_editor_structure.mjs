import {
  applyParsedCellEdit,
  deleteParsedColumn,
  deleteParsedRow,
  revertParsed,
} from "../app/web/editor_state.mjs";
import { toCsv } from "../app/web/csv_tools.mjs";

const parsed = {
  headers: ["sku", "price", "flag"],
  rows: [
    ["A", "1000", "Y"],
    ["B", "2000", "N"],
    ["C", "3000", ""],
  ],
  pristine: {
    headers: ["sku", "price", "flag"],
    rows: [
      ["A", "1000", "Y"],
      ["B", "2000", "N"],
      ["C", "3000", ""],
    ],
  },
  originalRows: [
    ["A", "1000", "Y"],
    ["B", "2000", "N"],
    ["C", "3000", ""],
  ],
  edits: new Set(),
  addedRowIndexes: new Set([2]),
  addedColumnIndexes: new Set([2]),
  structureDirty: true,
  dirty: true,
};

applyParsedCellEdit(parsed, 2, 1, "3100");
deleteParsedRow(parsed, 0);

if (!parsed.edits.has("1,1")) {
  throw new Error("row deletion should shift edited cell indexes");
}
if (!parsed.addedRowIndexes.has(1)) {
  throw new Error("row deletion should shift added row indexes");
}

deleteParsedColumn(parsed, 0);
if (!parsed.edits.has("1,0")) {
  throw new Error("column deletion should shift edited cell indexes");
}
if (!parsed.addedColumnIndexes.has(1)) {
  throw new Error("column deletion should shift added column indexes");
}

revertParsed(parsed);
if (parsed.dirty || parsed.structureDirty || parsed.edits.size !== 0) {
  throw new Error("revert should clear dirty state");
}
if (toCsv(parsed.headers, parsed.rows) !== toCsv(parsed.pristine.headers, parsed.pristine.rows)) {
  throw new Error("revert should restore pristine CSV");
}

console.log("editor structure verification passed");
