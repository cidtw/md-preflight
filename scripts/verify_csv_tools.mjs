import { parseCsv, toCsv } from "../app/web/csv_tools.mjs";

const cases = [
  "name,price\r\napple,1000\r\nbanana,2000\r\n",
  'name,note\r\n"kim, md","line 1\nline 2"\r\n',
  'code,message\r\nA1,"quote ""inside"" field"\r\n',
  "word,meaning\r\n안녕,hello\r\n,\r\n",
];

for (const [index, csv] of cases.entries()) {
  const parsed = parseCsv(csv);
  const roundTrip = parseCsv(toCsv(parsed.headers, parsed.rows));
  const lhs = JSON.stringify(parsed);
  const rhs = JSON.stringify(roundTrip);
  if (lhs !== rhs) {
    throw new Error(`CSV round-trip failed for case ${index + 1}`);
  }
}

const expandedHeaders = ["sku", "price", "promo_flag"];
const expandedRows = [
  ["SKU-1", "1000", ""],
  ["SKU-2", "2000", "Y"],
  ["", "", ""],
];
const expandedRoundTrip = parseCsv(toCsv(expandedHeaders, expandedRows));
if (JSON.stringify(expandedRoundTrip) !== JSON.stringify({ headers: expandedHeaders, rows: expandedRows })) {
  throw new Error("CSV structure expansion round-trip failed");
}

console.log("csv tools verification passed");
