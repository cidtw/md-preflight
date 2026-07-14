import { formatPreflightError } from "../app/web/error_format.mjs";

const col = formatPreflightError(
  422,
  "Missing columns in inventory: inbound_date, expected_demand (similar headers: inbound_date? 예:입고일,입고예정일; expected_demand? 예:예상수요,예상판매)",
);
if (!col.isColumnError) throw new Error("expected column error");
if (!col.body.includes("재고")) throw new Error("source label");
if (!col.body.includes("inbound_date")) throw new Error("missing col");
if (!col.body.includes("힌트")) throw new Error("hints");

const plain = formatPreflightError(500, "boom");
if (plain.isColumnError) throw new Error("not column");
if (plain.body !== "boom") throw new Error("body");

console.log("error_format verification passed");
