// Author SANZO-owned SDK inputs through the public Artifact Tool API.
import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [mode, outputDir, researchPath] = process.argv.slice(2);
await fs.mkdir(outputDir, { recursive: true });
const wb = Workbook.create();
const sheet = wb.worksheets.add(mode === 'smoke' ? 'Smoke' : 'Rates');
sheet.showGridLines = false;
let filename;
let renderRanges;
if (mode === 'smoke') {
filename = 'minimal.xlsx';
sheet.getRange('A1:C5').values = [
  ['SANZO SDK', null, null],
  ['Field', 'Value', 'Purpose'],
  ['Property', 'SANZO smoke fixture', 'Synthetic SDK fixture'],
  ['Price JPY', 12345678, 'Not a real property'],
  ['Publishable', false, 'Must not be published'],
];
sheet.getRange('A1:C5').format.font = { name: 'Arial', size: 11, color: '#1F2937' };
sheet.getRange('A1').format.font = { name: 'Arial', size: 16, bold: true };
sheet.getRange('A2:C2').format = { fill: '#213B35', font: { color: '#FFFFFF', bold: true }, rowHeight: 28 };
sheet.getRange('A1:C5').format.rowHeight = 28;
sheet.getRange('A1:A5').format.columnWidth = 30;
sheet.getRange('B1:B5').format.columnWidth = 28;
sheet.getRange('C1:C5').format.columnWidth = 28;
sheet.getRange('B4').setNumberFormat('#,##0');
renderRanges = ['A1:C5'];
} else if (mode === 'business') {
  if (!researchPath) throw new Error('Business workbook requires verified research.');
  const research = JSON.parse(await fs.readFile(researchPath, 'utf8'));
  filename = '住宅ローン_demo.xlsx';
  const headers = ['bank', 'product', 'rate_type', 'rate', 'effective_date', 'valid_until', 'notes', 'source_url', 'source_name', 'checked_at', 'rate_over_90_percent', 'years_min', 'years_max', 'loan_amount_min', 'loan_amount_max', 'max_loan_to_value'];
  const asDate = (value) => value ? new Date(`${value}T00:00:00Z`) : null;
  const rows = research.mortgage_rates.map(rate => [
    rate.bank, rate.product, rate.rate_type, rate.rate,
    asDate(rate.effective_date), asDate(rate.valid_until),
    `${rate.rate_label}。${rate.effective_period}。${rate.effective_date_basis} 利用条件：${rate.conditions.join('、')}。${rate.notes}`,
    rate.source_url, rate.source_name, asDate(rate.checked_at),
    rate.rate_over_90_percent ?? null, rate.years_min, rate.years_max,
    rate.loan_amount_min, rate.loan_amount_max, rate.max_loan_to_value ?? null,
  ]);
  sheet.getRange('A1:P3').values = [headers, ...rows];
  sheet.getRange('A1:P3').format.font = { name: 'Hiragino Sans', size: 11, color: '#1F2937' };
  sheet.getRange('A1:P3').format.verticalAlignment = 'center';
  sheet.getRange('A1:P1').format = { fill: '#213B35', font: { name: 'Arial', size: 11, color: '#FFFFFF', bold: true }, rowHeight: 34, horizontalAlignment: 'center' };
  sheet.getRange('A2:P3').format.rowHeight = 130;
  sheet.getRange('A2:P3').format.wrapText = true;
  sheet.getRange('A1:A3').format.columnWidth = 35;
  sheet.getRange('B1:B3').format.columnWidth = 48;
  sheet.getRange('C1:C3').format.columnWidth = 22;
  sheet.getRange('D1:D3').format.columnWidth = 16;
  sheet.getRange('E1:F3').format.columnWidth = 22;
  sheet.getRange('G1:G3').format.columnWidth = 94;
  sheet.getRange('H1:H3').format.columnWidth = 80;
  sheet.getRange('I1:I3').format.columnWidth = 45;
  sheet.getRange('J1:J3').format.columnWidth = 22;
  sheet.getRange('K1:K3').format.columnWidth = 28;
  sheet.getRange('L1:M3').format.columnWidth = 18;
  sheet.getRange('N1:O3').format.columnWidth = 24;
  sheet.getRange('P1:P3').format.columnWidth = 28;
  sheet.getRange('D2:D3').setNumberFormat('0.000" %"');
  sheet.getRange('K2:K3').setNumberFormat('0.00" %"');
  sheet.getRange('E2:F3').setNumberFormat('yyyy-mm-dd');
  sheet.getRange('J2:J3').setNumberFormat('yyyy-mm-dd');
  sheet.getRange('L2:M3').setNumberFormat('0" 年"');
  sheet.getRange('N2:O3').setNumberFormat('#,##0" 円"');
  sheet.getRange('P2:P3').setNumberFormat('0%');
  sheet.getRange('D2:F3').format.horizontalAlignment = 'right';
  sheet.getRange('J2:P3').format.horizontalAlignment = 'right';
  sheet.getRange('A2:P3').format.borders = { preset: 'inside', style: 'thin', color: '#D6DFD7' };
  sheet.freezePanes.freezeRows(1);
  sheet.tabColor = '#213B35';
  sheet.getRange('A5').values = [['住宅ローン参考金利']];
  sheet.getRange('A5').format.font = { name: 'Hiragino Sans', size: 16, bold: true, color: '#213B35' };
  sheet.getRange('A7').values = [['公開情報を基にSANZOがデモ用に再構成']];
  sheet.getRange('A8').values = [['基準日：2026-10-07。rateの数値単位は年利％（1.195は1.195％）。']];
  sheet.getRange('A9').values = [['参考金利は2026年10月借入／資金受取分。有効期限後は現行金利として使用しません。']];
  sheet.getRange('A10').values = [['融資可否は審査によります。フラット35は融資率9割超の場合、参考金利3.94％。']];
  sheet.getRange('A11').values = [['月額返済はDemoのBackendで計算します。このExcelは金利Master資料です。']];
  sheet.getRange('A12').values = [['本結果は概算です。実際の適用金利・融資条件等は金融機関により異なります。']];
  sheet.getRange('A7:G12').format.font = { name: 'Hiragino Sans', size: 11, color: '#43584D' };
  sheet.getRange('A7:G12').format.rowHeight = 28;
  renderRanges = ['A1:G3', 'H1:P3', 'A5:G12'];
} else {
  throw new Error(`Unknown generation mode: ${mode}`);
}
wb.recalculate();
const evidenceDir = mode === 'smoke' ? outputDir : path.join(outputDir, '../evidence/documents');
await fs.mkdir(evidenceDir, { recursive: true });
const check = await wb.inspect({ kind: 'table', range: `${sheet.name}!${mode === 'smoke' ? 'A1:C5' : 'A1:P3'}`, include: 'values,formulas', tableMaxRows: 5, tableMaxCols: 16 });
await fs.writeFile(path.join(evidenceDir, 'workbook_inspect.ndjson'), check.ndjson);
for (let i = 0; i < renderRanges.length; i++) {
  const preview = await wb.render({ sheetName: sheet.name, range: renderRanges[i], scale: 1.25, format: 'png' });
  const previewName = mode === 'smoke' ? 'workbook_preview.png' : `mortgage_preview_${i + 1}.png`;
  await fs.writeFile(path.join(evidenceDir, previewName), new Uint8Array(await preview.arrayBuffer()));
}
const exported = await SpreadsheetFile.exportXlsx(wb);
await exported.save(path.join(outputDir, filename));
const exportInspect = path.join(outputDir, `${filename}.inspect.ndjson`);
try {
  await fs.rename(exportInspect, path.join(evidenceDir, `${filename}.inspect.ndjson`));
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
console.log(`Workbook generated and rendered: ${filename}`);
