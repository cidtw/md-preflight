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

console.log("csv tools verification passed");
