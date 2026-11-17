import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const base = path.dirname(scriptDir);
const csvPath = path.join(base, "resultados", "resultados_scan_IA", "tabela_final_humano_x_ia.csv");
const outputPath = path.join(base, "resultados", "resultados_scan_IA", "tabela_final_humano_x_ia.xlsx");
const csvText = (await fs.readFile(csvPath, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Comparativo" });
const sheet = workbook.worksheets.getItem("Comparativo");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(2);

const used = sheet.getUsedRange();
used.format.font = { name: "Arial", size: 10, color: "#1F2937" };
used.format.verticalAlignment = "center";
const header = used.getRow(0);
header.format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#163A5C" },
};
header.format.rowHeight = 36;

const values = used.values;
const headers = values[0];
const numericHeaders = new Set([
  "execucao", "temperatura", "python_loc", "semgrep_total", "semgrep_error",
  "semgrep_warning", "semgrep_info", "semgrep_erros_operacionais", "semgrep_por_kloc",
  "sonarqube_total", "sonarqube_vulnerabilidades", "sonarqube_bugs",
  "sonarqube_code_smells", "sonarqube_hotspots", "sonarqube_complexidade",
  "sonarqube_ncloc", "sonarqube_por_kloc",
]);
for (let col = 0; col < headers.length; col += 1) {
  if (!numericHeaders.has(headers[col])) continue;
  for (let row = 1; row < values.length; row += 1) {
    const value = values[row][col];
    if (value !== "" && value !== null && value !== undefined && !Number.isNaN(Number(value))) {
      sheet.getCell(row, col).values = [[Number(value)]];
    }
  }
}

used.format.autofitColumns();
used.format.autofitRows();
for (let col = 0; col < headers.length; col += 1) {
  const column = used.getColumn(col);
  const name = headers[col];
  if (["github", "link_commit", "semgrep_cwes", "observacoes"].includes(name)) {
    column.format.columnWidth = name === "semgrep_cwes" ? 45 : 32;
    column.format.wrapText = true;
  } else {
    column.format.columnWidth = Math.min(column.format.columnWidth || 14, 22);
  }
}

const lastRow = values.length;
const lastColNumber = headers.length;
function columnName(n) {
  let result = "";
  while (n > 0) {
    n -= 1;
    result = String.fromCharCode(65 + (n % 26)) + result;
    n = Math.floor(n / 26);
  }
  return result;
}
const table = sheet.tables.add(`A1:${columnName(lastColNumber)}${lastRow}`, true, "ComparativoHumanoIA");
table.style = "TableStyleMedium2";
table.showFilterButton = true;
table.showBandedRows = true;

const originIndex = headers.indexOf("origem");
if (originIndex >= 0 && lastRow > 1) {
  const originRange = sheet.getRangeByIndexes(1, originIndex, lastRow - 1, 1);
  originRange.conditionalFormats.add("containsText", {
    text: "humano",
    format: { fill: "#DCE6F1", font: { bold: true, color: "#1F4E78" } },
  });
}

workbook.recalculate();
const check = await workbook.inspect({
  kind: "table",
  range: `Comparativo!A1:${columnName(lastColNumber)}${lastRow}`,
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 34,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);
const preview = await workbook.render({ sheetName: "Comparativo", range: `A1:L${lastRow}`, scale: 1.2, format: "png" });
const validationDir = path.join(scriptDir, "validacao");
await fs.mkdir(validationDir, { recursive: true });
await fs.writeFile(path.join(validationDir, "tabela_final_preview.png"), new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(outputPath);
