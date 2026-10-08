# Web backend integration

The SDK is a synchronous Python library, not a Web server. FastAPI/Flask/Django remain application dependencies. No global SDK initialization or API key is needed for these local operations.

The following application helper accepts an already opened binary upload stream. Its PDF branch returns **inspection**, not full document extraction; use `extract_native_text` or the actual `analyze_pdf`/`analyze_document` APIs for analysis. Its Excel branch returns only the explicitly requested range. It does not claim the rest of the workbook was extracted.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import BinaryIO

from document_sdk.core import DocumentProcessingError, DocumentSdkError
from document_sdk.excel import read_range
from document_sdk.pdf import PdfProcessingLimits, inspect_pdf

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # Application upload policy, not an SDK default.
PDF_LOCK = Lock()  # All PDFium calls in this app process must use one shared gate.

def process_upload(stream: BinaryIO, suffix: str, sheet_name: str | None = None) -> dict:
    if suffix not in {".pdf", ".xlsx", ".xlsm"}:
        raise ValueError("Unsupported route format")
    with TemporaryDirectory(prefix="document-upload-") as directory:
        path = Path(directory) / ("input" + suffix)
        size = 0
        with path.open("wb") as target:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise ValueError("Upload exceeds the application limit")
                target.write(chunk)
        try:
            if suffix == ".pdf":
                limits = PdfProcessingLimits(
                    max_file_bytes=MAX_UPLOAD_BYTES,
                    max_pages=100,
                    max_native_text_pages=100,
                )
                with PDF_LOCK:
                    result = inspect_pdf(path, limits=limits)
            else:
                if not sheet_name:
                    raise ValueError("Exact worksheet name is required")
                result = read_range(
                    path, sheet_name, "A1:D100", max_cells=400, formula_view="both"
                )
            return {"ok": True, "data": result.model_dump(mode="json")}
        except DocumentProcessingError:
            return {"ok": False, "error": {"code": "processing_failed"}}
        except DocumentSdkError as exc:
            return {"ok": False, "error": {"code": type(exc).__name__}}
```

FastAPI supplies `UploadFile.file`, Flask supplies `FileStorage.stream`, and Django's uploaded-file object supports binary reads. Call this helper from a bounded synchronous worker; do not run blocking parsing directly on an async event loop. Framework/proxy request size limits must also apply before multipart parsing. Select permitted suffixes in the application; a name or content-type header does not establish file validity, and the SDK validates content at its boundary.

A success has `ok=true` and the SDK model serialized under `data`: PDF inspection includes `page_count` and `pages`; Excel results include `sheet_name` and `cells` with coordinates, values/formula/cache distinctions and source references. Do not discard warnings or interpret inspection as full semantic extraction. `file_id` and content fingerprint have different meanings.

Handle `ValueError`/validation failures as invalid application parameters and translate SDK errors into your chosen HTTP error policy. Do not send traceback, input contents, raw provider exceptions or credentials to clients. `DocumentProcessingError` alone does not cover all SDK resource/format/access errors; `DocumentSdkError` is the expected failure-family base.

Use a unique temp directory per request, stable input bytes during parsing, explicit upload/cell/page/pixel/package limits and bounded concurrency. The example's 20 MiB upload limit is application policy. SDK defaults and real public signatures appear in PUBLIC_API.md. `read_sheet` defaults to `max_cells=None`, so use an explicit cap. Streaming Excel iterators must be fully consumed or explicitly closed before deleting their input; `contextlib.closing` is suitable when early termination is possible.

Do not share open PDFium documents across threads. Direct PDF calls need process-wide serialization; a isolated worker process also permits hard timeout/resource termination. The SDK's existing Batch path has its own PDF analysis lock, but the simple helper above uses a shared application lock for direct calls. A cancelled async task or thread timeout does not safely interrupt native parsing. Excel requests must not concurrently patch the same workbook. OCR engine sharing must obey that engine's declared concurrency policy; cloud-backed batch worker restrictions still apply.

The example closes output files before parsing and cleans temporary input in `TemporaryDirectory` on success or exceptions. The caller owns and closes the original upload stream. Process-local temp cleanup after forced termination remains an application lifecycle responsibility. Never keep user originals inside `site-packages/document_sdk` or the vendor bundle. Choose retention, storage, identity and access policies in the Web application.

For DOCX use `inspect_docx`/`analyze_docx`; for images use `inspect_image` and explicit optional OCR if required. Unified `analyze_document` keeps providers explicit and, for Excel, returns workbook inspection rather than reading every cell. There is no automatic OpenAI/cloud fallback. Additional services must be explicitly provisioned and selected by the application.

The snippet was syntax-checked and its underlying PDF/Excel APIs exercised in the local installation smoke. No FastAPI/Flask/Django server was installed or deployed in this task.
