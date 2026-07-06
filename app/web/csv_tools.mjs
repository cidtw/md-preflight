export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1] ?? "";

    if (inQuotes) {
      if (char === '"' && next === '"') {
        field += '"';
        index += 1;
        continue;
      }
      if (char === '"') {
        inQuotes = false;
        continue;
      }
      field += char;
      continue;
    }

    if (char === '"') {
      inQuotes = true;
      continue;
    }
    if (char === ",") {
      row.push(field);
      field = "";
      continue;
    }
    if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      continue;
    }
    if (char === "\r") {
      continue;
    }
    field += char;
  }

  row.push(field);
  rows.push(row);

  const normalizedRows = rows.filter(
    (candidate, candidateIndex) =>
      candidateIndex < rows.length - 1 ||
      candidate.length > 1 ||
      candidate[0] !== "",
  );
  const headers = normalizedRows[0] ?? [];
  if (headers.length === 0) {
    throw new Error("CSV 헤더를 읽을 수 없습니다.");
  }

  const bodyRows = normalizedRows.slice(1).map((candidate) => {
    const padded = candidate.slice(0, headers.length);
    while (padded.length < headers.length) {
      padded.push("");
    }
    return padded;
  });

  return { headers, rows: bodyRows };
}

export function toCsv(headers, rows) {
  const normalizedRows = rows.map((row) => {
    const padded = row.slice(0, headers.length);
    while (padded.length < headers.length) {
      padded.push("");
    }
    return padded;
  });
  const lines = [headers, ...normalizedRows].map((row) =>
    row.map((value) => escapeCsvField(value ?? "")).join(","),
  );
  return `${lines.join("\r\n")}\r\n`;
}

export function isCsvFilename(name) {
  return name.toLowerCase().endsWith(".csv");
}

export function isSpreadsheetFilename(name) {
  return name.toLowerCase().endsWith(".xlsx");
}

export function buildEditedCsvFilename(fileKey, now = new Date()) {
  const timestamp = [
    now.getFullYear(),
    pad2(now.getMonth() + 1),
    pad2(now.getDate()),
  ].join("-");
  const time = `${pad2(now.getHours())}${pad2(now.getMinutes())}`;
  return `${fileKey}-edited-${timestamp}-${time}.csv`;
}

function escapeCsvField(value) {
  const normalized = String(value);
  if (
    normalized.includes(",") ||
    normalized.includes("\n") ||
    normalized.includes("\r") ||
    normalized.includes('"')
  ) {
    return `"${normalized.replaceAll('"', '""')}"`;
  }
  return normalized;
}

function pad2(value) {
  return String(value).padStart(2, "0");
}
