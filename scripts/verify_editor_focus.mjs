import { applyParsedCellEdit } from "../app/web/editor_state.mjs";

const parsed = {
  rows: [[""]],
  originalRows: [[""]],
  edits: new Set(),
  dirty: false,
};

applyParsedCellEdit(parsed, 0, 0, "가");
applyParsedCellEdit(parsed, 0, 0, "가나");
applyParsedCellEdit(parsed, 0, 0, "가나다123");

if (parsed.rows[0][0] !== "가나다123") {
  throw new Error("editor input did not accumulate correctly");
}
if (!parsed.dirty || parsed.edits.size !== 1) {
  throw new Error("editor dirty tracking failed");
}

console.log("editor focus verification passed");
