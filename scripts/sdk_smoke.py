"""Exercise the installed SANZO package only. No parsing fallback."""
import inspect
import json
import sys
from importlib.metadata import version
from pathlib import Path

import document_sdk
from document_sdk.excel import inspect_workbook, read_sheet
from document_sdk.pdf import PdfProcessingLimits, extract_native_text

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert Path(document_sdk.__file__).is_relative_to(ROOT / 'backend/.venv')
    pdf = extract_native_text(ROOT / 'demo_documents/smoke/minimal.pdf', limits=PdfProcessingLimits(max_pages=5, max_native_text_pages=5))
    workbook = inspect_workbook(ROOT / 'demo_documents/smoke/minimal.xlsx')
    excel = read_sheet(ROOT / 'demo_documents/smoke/minimal.xlsx', 'Smoke', max_cells=100)
    out = ROOT / 'evidence/sdk'
    out.mkdir(exist_ok=True, parents=True)
    raw = {'pdf': pdf.model_dump(mode='json'), 'workbook': workbook.model_dump(mode='json'), 'excel': excel.model_dump(mode='json')}
    (out / 'smoke_raw.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2))
    assert 'SANZO SDK' in json.dumps(raw['pdf'])
    assert 'SANZO SDK' in json.dumps(raw['excel'])
    result = {'status': 'PASS', 'sdk_version': version('document-processing-sdk'), 'import_file': document_sdk.__file__, 'python': sys.version.split()[0], 'apis': {f.__name__: str(inspect.signature(f)) for f in [extract_native_text, inspect_workbook, read_sheet]}, 'result_keys': {k: list(v) for k, v in raw.items()}, 'errors': []}
    (out / 'smoke_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
