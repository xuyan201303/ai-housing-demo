"""Only this adapter imports SANZO SDK. No parser implementation/fallback."""
import re
from importlib.metadata import version
from pathlib import Path
from threading import Lock
from document_sdk.core import DocumentSdkError
from document_sdk.pdf import PdfProcessingLimits, extract_native_text
from document_sdk.excel import ExcelPackageLimits, inspect_workbook, read_sheet
from app.models.domain import AppError

PDF_LOCK = Lock()
PROPERTY_KEYS = {'property_name', 'lot', 'price', 'address', 'station', 'walking_minutes', 'layout', 'land_area', 'building_area', 'parking', 'completion_date', 'equipment', 'surroundings', 'source_url', 'source_name', 'checked_at', 'effective_date', 'valid_until', 'scope_notes'}


class DocumentSdkAdapter:
    sdk_version = version('document-processing-sdk')

    def parse(self, path: Path, document_id: str, filename: str) -> dict:
        reference = {'document_id': document_id, 'filename': filename}
        normalized = {'property': {}, 'knowledge': [], 'rates': [], 'faq': []}
        try:
            if path.suffix.lower() == '.pdf':
                limits = PdfProcessingLimits(max_file_bytes=10*1024*1024, max_pages=30, max_native_text_pages=30, max_native_text_characters=200000)
                with PDF_LOCK:
                    result = extract_native_text(path, limits=limits)
                raw = result.model_dump(mode='json')
                for page in raw['pages']:
                    text = '\n'.join(block['text'] for block in page['text_blocks'])
                    if not text.strip():
                        continue
                    ref = dict(reference, location=f"p.{page['page_number']}")
                    normalized['knowledge'].append({'text': text, 'reference': ref})
                    logical_lines = []
                    for line in text.splitlines():
                        if re.match(r'^[a-z_]+\s*[:：]', line):
                            logical_lines.append(line)
                        elif logical_lines and line.strip() not in {'確認事項'} and not line.startswith('公開情報'):
                            # Join visual line wraps in our key:value demo documents.
                            # Native extraction remains exactly preserved under raw.
                            logical_lines[-1] += line.strip()
                        else:
                            logical_lines.append('')
                    for line in logical_lines:
                        match = re.match(r'^([a-z_]+)\s*[:：]\s*(.+)$', line.strip())
                        if match and match[1] in PROPERTY_KEYS:
                            key, value = match.groups()
                            if key in {'price', 'land_area', 'building_area', 'walking_minutes'}:
                                try:
                                    value = float(value.replace(',', ''))
                                except ValueError:
                                    pass
                            if key in {'equipment', 'surroundings'}:
                                normalized['property'].setdefault(key, []).append(value)
                            elif key in {'source_name', 'source_url'}:
                                normalized['property'].setdefault(key, value)
                            else:
                                normalized['property'][key] = value
                if not normalized['knowledge']:
                    raise AppError('NO_NATIVE_TEXT', '文字を取得できませんでした。画像PDFのOCRは未設定です。', 422)
                api = 'document_sdk.pdf.extract_native_text'
            elif path.suffix.lower() == '.xlsx':
                inspection = inspect_workbook(path, package_limits=ExcelPackageLimits(package_members=1000, total_uncompressed_bytes=20000000, xml_member_bytes=10000000, compression_ratio=200))
                if len(inspection.sheet_names) > 10:
                    raise AppError('SHEET_LIMIT', 'シート数は10以下にしてください。', 422)
                sheets = []
                for name in inspection.sheet_names:
                    sheet = read_sheet(path, name, max_cells=10000, formula_view='both').model_dump(mode='json')
                    sheets.append(sheet)
                    rows = {}
                    for cell in sheet['cells']:
                        # Formula evidence is retained in raw; cached/formula cells aren't facts.
                        if cell.get('formula') or cell.get('formula_text'):
                            continue
                        col, row = re.match(r'([A-Z]+)(\d+)', cell['coordinate']).groups()
                        rows.setdefault(int(row), {})[col] = cell['value']
                    if not rows:
                        continue
                    ref = dict(reference, location=name)
                    for row_number, row in sorted(rows.items()):
                        normalized['knowledge'].append({'text': ' | '.join(str(v) for v in row.values()), 'reference': dict(ref, location=f'{name}!{row_number}')})
                    # Require an explicit header row; never guess financial columns.
                    header_row = next((r for r, cols in sorted(rows.items()) if 'bank' in cols.values() and 'rate' in cols.values()), None)
                    if header_row:
                        headers = rows[header_row]
                        for r, cols in sorted(rows.items()):
                            if r <= header_row:
                                continue
                            rate = {str(headers[c]): v for c, v in cols.items() if c in headers}
                            for key in ['effective_date', 'valid_until', 'checked_at']:
                                if isinstance(rate.get(key), str):
                                    rate[key] = rate[key].split('T')[0]
                            if rate.get('bank') and isinstance(rate.get('rate'), (float, int)):
                                rate['id'] = f'{document_id}:{name}:{r}'
                                rate['reference'] = dict(ref, location=f'{name}!{r}')
                                normalized['rates'].append(rate)
                raw = {'inspection': inspection.model_dump(mode='json'), 'sheets': sheets}
                api = 'document_sdk.excel.inspect_workbook + read_sheet'
                if normalized['rates']:
                    # Financial rows must go through the date/condition-aware rate tool,
                    # never become unfiltered document knowledge.
                    normalized['knowledge'] = []
            else:
                raise AppError('UNSUPPORTED_FILE', 'PDF / XLSX のみ対応しています。', 415)
        except DocumentSdkError as exc:
            raise AppError('SDK_' + type(exc).__name__, 'SANZO SDK 解析に失敗しました。資料形式・上限を確認してください。', 422) from exc
        except (ValueError, TypeError) as exc:
            raise AppError('SDK_INVALID_INPUT', 'SANZO SDK が資料を処理できませんでした。', 422) from exc
        if path.suffix.lower()=='.pdf':
            all_text='\n'.join(i['text'] for i in normalized['knowledge'])
            match=re.search(r'^knowledge_scope:\s*(general|company)\s*$',all_text,re.M)
            if match:
                normalized['document']=dict(normalized['property'],scope=match[1])
                normalized['property']={}
        return {'raw': raw, 'normalized': normalized, 'sdk_version': self.sdk_version, 'sdk_api': api}
