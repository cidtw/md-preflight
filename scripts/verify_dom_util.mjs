import { ext, fmtSize } from "../app/web/dom_util.mjs";

if (ext("file.XLSX") !== ".xlsx") throw new Error("ext case");
if (ext("noext") !== "") throw new Error("ext empty");
if (fmtSize(0) !== "0 B") throw new Error("fmt 0");
if (fmtSize(2048) !== "2.0 KB") throw new Error("fmt kb");
if (!fmtSize(3 * 1024 * 1024).includes("MB")) throw new Error("fmt mb");
console.log("dom_util verification passed");
