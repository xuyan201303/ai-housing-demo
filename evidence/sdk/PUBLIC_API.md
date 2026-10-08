# Public API — document-processing-sdk 1.8.0

Source commit: `287914d4e000b4c3f312b045766e784291d257ae`. Enumerated from the installed wheel, using explicit public package `__all__` exports. Private modules/helpers are excluded. Import name: `document_sdk`.

## Main entry points

| Module | Entry points and purpose |
| --- | --- |
| `document_sdk.document` | `detect_document_type`, `inspect_document`, `analyze_document`: local family dispatch; Excel analysis retains workbook inspection, not a replacement for explicit cell reads. |
| `document_sdk.pdf` | `inspect_pdf`, `extract_native_text`, `render_page`, `render_region`, `analyze_pdf`: inspection, native text, rendering and unified PDF analysis. |
| `document_sdk.excel` | `inspect_workbook`, `read_range`, `read_sheet`, `iter_non_empty_cells`, `iter_rows`, `inspect_workbook_semantic_details`, `compare_workbooks`, `patch_workbook`, `write_workbook`. |
| `document_sdk.docx` | `inspect_docx`, `analyze_docx`: local OOXML Word structure. |
| `document_sdk.image` | `inspect_image`, bounded image reads/transforms/comparison and explicit OpenCV operations. |
| Other exported modules below | Typed OCR/provider, extraction, batch/workflow and source/result models. Cloud/OCR use requires explicit configuration. |

Supported content families: PDF; OOXML `.xlsx`/`.xlsm`; `.docx`; PNG/JPEG/TIFF/WebP/BMP. Legacy `.xls`/`.xlsb`, encrypted Office/PDF, arbitrary ZIPs and macro execution are not promised by these entry points. Per-operation restrictions still apply: workbook writing creates `.xlsx`; formulas are read/preserved, not recalculated by Excel; local DOCX analysis does not emulate Word pagination. A detected or inspectable format does not imply every feature has an extraction API.

`path` means a stable local `pathlib.Path`; `sheet_name` is the exact worksheet name; ranges use inclusive A1 coordinates; page numbers are 1-based. Models are SDK-owned and carry source references. `file_id` is caller-owned logical identity; fingerprints identify bytes. Return annotations and each function's actual parameter documentation follow below.

## Resource limits

Defaults below are read from the installed public models, not suggested upload limits. Web applications should use stricter appropriate limits. `read_sheet(max_cells=None)` has no configured rectangular cell-count cap; always specify a cap for untrusted files. `read_range` defaults to 100000 requested rectangular cells. Streaming API bounds, formula projection and package limits are shown in their signatures. File upload bytes and hard wall-clock timeouts remain application responsibilities.

### `PdfProcessingLimits`

```json
{
  "max_file_bytes": 512000000,
  "max_pages": 1000,
  "max_page_width_points": 10000.0,
  "max_page_height_points": 10000.0,
  "max_page_area_points": 50000000.0,
  "max_native_text_pages": 1000,
  "max_native_text_characters": 20000000,
  "max_render_dpi": 300,
  "max_render_width": 20000,
  "max_render_height": 20000,
  "max_render_pixels": 25000000,
  "max_output_bytes": 20000000
}
```

### `ExcelPackageLimits`

```json
{
  "package_members": 10000,
  "total_uncompressed_bytes": 536870912,
  "xml_member_bytes": 67108864,
  "compression_ratio": 1000,
  "worksheet_feature_records": 100000,
  "shared_string_entries": 1000000,
  "semantic_detail_records": 1000000,
  "semantic_detail_text_characters": 67108864,
  "semantic_detail_xml_depth": 256
}
```

### `DocxProcessingLimits`

```json
{
  "max_input_bytes": 512000000,
  "max_package_members": 10000,
  "max_total_uncompressed_bytes": 1000000000,
  "max_member_uncompressed_bytes": 256000000,
  "max_compression_ratio": 200.0,
  "max_xml_parts": 2000,
  "max_total_xml_bytes": 256000000,
  "max_xml_part_bytes": 32000000,
  "max_xml_elements": 2000000,
  "max_xml_depth": 256,
  "max_relationships": 100000,
  "max_text_characters": 100000000,
  "max_paragraphs": 2000000,
  "max_runs": 10000000,
  "max_tables": 100000,
  "max_table_rows": 2000000,
  "max_table_cells": 10000000,
  "max_nested_table_depth": 32,
  "max_sections": 100000,
  "max_headers": 10000,
  "max_footers": 10000,
  "max_comments": 1000000,
  "max_footnotes": 1000000,
  "max_endnotes": 1000000,
  "max_hyperlinks": 2000000,
  "max_bookmarks": 2000000,
  "max_content_controls": 2000000,
  "max_media_parts": 100000,
  "max_embedded_parts": 100000,
  "max_embedded_total_bytes": 512000000
}
```

### `ImageProcessingLimits`

```json
{
  "max_frames": 100,
  "max_pixels_per_frame": 25000000,
  "max_total_pixels": 100000000,
  "max_working_pixels": 50000000,
  "max_output_bytes": 50000000,
  "max_output_width": 20000,
  "max_output_height": 20000
}
```

## Public exceptions

Catch `DocumentSdkError` for the expected SDK failure family. `DocumentProcessingError` is one subclass; dependency, format, resource and access failures may be siblings. Caller parameter validation can also raise `ValueError`/Pydantic validation errors.

- `document_sdk.batch.BatchConfigurationError` — Raised for invalid global batch configuration. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.batch.BatchManifestError` — Raised when a persisted manifest is invalid or incompatible. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.batch.BatchProcessingLimitError` — Raised when discovery cannot remain inside a global safety limit. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.batch.BatchResultValidationError` — Raised when public Batch evidence is inconsistent. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.CredentialResolutionError` — Raised when a runtime credential resolver cannot resolve credentials. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.DependencyNotInstalledError` — Raised when an optional feature dependency is unavailable. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.DocumentProcessingError` — Raised when document processing fails after input validation. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.DocumentSdkError` — Base class for all expected SDK failures. (bases: Exception, BaseException).
- `document_sdk.core.EncryptedDocumentError` — Raised when an encrypted document cannot be processed. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ExcelCellLimitExceededError` — Raised before an Excel read would exceed its configured cell limit. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.FileAccessError` — Raised when a local file cannot be accessed safely. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ImageLimitExceededError` — Raised before image decoding would exceed a configured limit. (bases: ImageProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ImageProcessingError` — Raised when local image inspection cannot complete safely. (bases: DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.core.InvalidSourceReferenceError` — Raised when source information cannot identify a valid origin. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderAuthenticationError` — Raised when a provider rejects the resolved authentication. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderAuthorizationError` — Raised when the resolved identity cannot perform the operation. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderConfigurationError` — Raised when provider configuration is invalid for an operation. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderRateLimitError` — Raised when a provider rate limit temporarily rejects work. (bases: ProviderUnavailableError, DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderRequestError` — Raised when a provider rejects a non-authentication request. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderResponseError` — Raised when a provider returns malformed or unsafe result data. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderTimeoutError` — Raised when a provider operation exceeds its configured wait. (bases: ProviderUnavailableError, DocumentSdkError, Exception, BaseException).
- `document_sdk.core.ProviderUnavailableError` — Raised when an explicitly selected provider cannot be reached or used. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.core.UnsupportedFileError` — Raised when a file type is outside an API's supported formats. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.document.DocumentResultValidationError` — Raised when public Unified Document evidence is inconsistent. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.document.DocumentSourceChangedError` — Raised when source bytes change during one document operation. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.document.DocumentTypeMismatchError` — Raised when a requested operation is incompatible with the content. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.document.UnsupportedDocumentOperationError` — Raised when a document family cannot perform a requested operation. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.document.UnsupportedDocumentTypeError` — Raised when content is not one of the supported document families. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.docx.DocxPackageInvalidError` — Raised when an OPC/ZIP or XML contract is malformed. (bases: DocxProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.docx.DocxProcessingError` — Base failure for local DOCX inspection and analysis. (bases: DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.docx.DocxResourceLimitError` — Raised before configured DOCX resource limits would be exceeded. (bases: DocxProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.docx.DocxSourceChangedError` — Raised when authorized source bytes change during one operation. (bases: DocxProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.docx.DocxUnsupportedPackageError` — Raised when an Office package is not a supported non-macro DOCX. (bases: DocxProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.excel.ExcelComparisonLimitError` — Raised when comparison input exceeds its configured cell bound. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.excel.ExcelModificationError` — Raised when a requested workbook modification is invalid or unsafe. (bases: DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.excel.ExcelPackageLimitError` — Raised before unsafe OOXML package expansion. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.excel.UnsupportedWorkbookFeatureError` — Raised for a specifically unsupported workbook feature request. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.excel.WorkbookPreservationError` — Raised when strict preservation rejects present workbook features. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.extraction.ExtractionSchemaError` — Raised when an extraction request does not contain a valid schema. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.extraction.StructuredExtractionIncompleteError` — Raised after a validated result is incomplete when fail-fast is enabled. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.extraction.StructuredExtractionProviderRequiredError` — Raised when the selected extraction strategy requires a Provider. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.image.ImageAlignmentError` — Raised when bounded alignment has insufficient geometric evidence. (bases: ImageProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.image.ImagePreservationError` — Raised when strict image preservation cannot be guaranteed. (bases: ImageProcessingError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackConfigurationError` — Raised when explicit fallback configuration is incomplete. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackError` — Base class for controlled Azure fallback failures. (bases: DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackExecutionError` — Raised when the Azure Provider fails at the fallback boundary. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackInvalidResultError` — Raised when Azure returns incomplete or inconsistent evidence. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackLimitError` — Raised before fallback would exceed an explicit resource limit. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackMappingError` — Raised when isolated payload results cannot map to source indexes. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackPayloadError` — Raised when an isolated payload cannot be created safely. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackProviderTypeError` — Raised when fallback receives a non-Azure Provider implementation. (bases: AzureFallbackConfigurationError, AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackResumeIdentityMismatchError` — Raised when fallback identity differs from retained Resume evidence. (bases: AzureFallbackError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.AzureFallbackSourceChangedError` — Raised when the caller's original source changes during fallback. (bases: AzureFallbackError, DocumentProcessingError, DocumentSourceChangedError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrEngineIdentityError` — Raised when runtime Engine identity is incompatible with retained evidence. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrEngineInitializationError` — Raised when an explicit Engine cannot be safely initialized. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrError` — Base for controlled Local OCR failures. (bases: DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrExecutionError` — Raised when local Engine inference fails. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrInvalidResultError` — Raised when an Engine returns malformed or unsafe output. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrLimitExceededError` — Raised before a configured Local OCR resource bound is exceeded. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrModelSelectionError` — Raised before work when a Local OCR model selection is unsupported. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrModelUnavailableError` — Raised when caller-managed local model data is unavailable. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrPreprocessingConfigurationError` — The explicit preprocessing configuration is invalid. (bases: LocalOcrPreprocessingError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrPreprocessingError` — Base preprocessing failure. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrPreprocessingExecutionError` — An in-memory preprocessing profile failed. (bases: LocalOcrPreprocessingError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrPreprocessingLimitError` — A preprocessing attempt or pixel limit was exceeded. (bases: LocalOcrLimitExceededError, LocalOcrPreprocessingError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrPreprocessingSelectionError` — Candidate quality evidence could not be selected consistently. (bases: LocalOcrPreprocessingError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrQualityConfigurationError` — Raised before processing when Local OCR quality policy is incompatible. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrQualityEvaluationError` — Raised when quality evidence cannot be evaluated safely. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrUnsupportedInputError` — Raised when content is not a supported PDF or image family. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.LocalOcrUnsupportedLanguageError` — Raised before work when a Local OCR language profile is unsupported. (bases: LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.RapidOcrEngineInitializationError` — Raised when the fixed CPU runtime cannot be initialized safely. (bases: RapidOcrError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.RapidOcrExecutionError` — Raised for inference failures or unsupported third-party output. (bases: RapidOcrError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.ocr.RapidOcrModelValidationError` — Raised when a local ONNX model set violates its declared identity. (bases: RapidOcrError, LocalOcrError, DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.pdf.PdfLimitExceededError` — Raised before PDF processing would exceed a configured limit. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.pdf.PdfRenderLimitExceededError` — Raised before PDF rendering or encoding exceeds a configured limit. (bases: PdfLimitExceededError, DocumentSdkError, Exception, BaseException).
- `document_sdk.pipeline.OcrProviderRequiredError` — Raised when OCR-candidate PDF pages require an explicit Provider. (bases: DocumentProcessingError, DocumentSdkError, Exception, BaseException).
- `document_sdk.workflow.DocumentWorkflowArtifactError` — Raised when a caller-owned artifact cannot be trusted or accessed. (bases: DocumentWorkflowError, DocumentSdkError, Exception, BaseException).
- `document_sdk.workflow.DocumentWorkflowConfigurationError` — Raised when a workflow request or Provider bundle is inconsistent. (bases: DocumentWorkflowError, DocumentSdkError, Exception, BaseException).
- `document_sdk.workflow.DocumentWorkflowError` — Base class for expected one-file workflow failures. (bases: DocumentSdkError, Exception, BaseException).
- `document_sdk.workflow.DocumentWorkflowResultValidationError` — Raised when public workflow evidence is inconsistent. (bases: DocumentWorkflowError, DocumentSdkError, Exception, BaseException).
- `document_sdk.workflow.DocumentWorkflowResumeError` — Raised when prior stage evidence cannot be resumed safely. (bases: DocumentWorkflowError, DocumentSdkError, Exception, BaseException).

## `document_sdk`


### `__version__` (value)


str(object='') -> str

## `document_sdk.batch`


### `BatchAzureFallbackAggregate` (class)

```python
BatchAzureFallbackAggregate(*, evaluated: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, not_needed: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, completed: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, unresolved: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, failed: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, page_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, frame_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, provider_invocation_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, confirmed_azure_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, confirmed_paid_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, payload_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, payload_byte_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, reason_counts: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCount, ...], MaxLen(max_length=8)] = ()) -> None
```

Content-free aggregate of explicit Azure fallback outcomes.

### `BatchConfigurationError` (exception)


Raised for invalid global batch configuration.

### `BatchDocumentInput` (class)

```python
BatchDocumentInput(*, input_id: 'str', relative_name: 'str', source: 'Path | str') -> None
```

One input whose local source exists only as private runtime state.

### `BatchItemIssue` (class)

```python
BatchItemIssue(*, code: Annotated[str, MinLen(min_length=1)], category: Annotated[str, MinLen(min_length=1)], message: Annotated[str, MinLen(min_length=1)]) -> None
```

Content-free per-item issue.

### `BatchItemResult` (class)

```python
BatchItemResult(*, input_id: Annotated[str, Strict(strict=True), MinLen(min_length=1), MaxLen(max_length=128), AfterValidator(func=<function _validate_batch_input_id at 0x10bb92ca0>)], relative_name: Annotated[str, MinLen(min_length=1)], status: document_sdk.batch.models.BatchItemStatus, intake_status: document_sdk.workflow.models.DocumentWorkflowIntakeStatus | None = None, duplicate_of: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[Strict(strict=True), MinLen(min_length=1), MaxLen(max_length=128)]), AfterValidator(func=<function _validate_batch_input_id at 0x10bb92ca0>)]] = None, duplicate_identity_kind: Optional[Literal['source_sha256']] = None, issues: tuple[document_sdk.batch.models.BatchItemIssue, ...] = (), source_sha256: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, byte_size: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, consumed_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, document_type: document_sdk.document.models.DocumentType | None = None, document_format: document_sdk.document.models.DocumentFormat | None = None, pdf_page_count: Annotated[int | None, Strict(strict=True), Ge(ge=1)] = None, excel_worksheet_count: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, image_frame_count: Annotated[int | None, Strict(strict=True), Ge(ge=1)] = None, docx_block_count: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, result_fingerprint: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, resume_eligible_success: bool = False, performed_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), retained_prior_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_usage: document_sdk.core.models.ProviderUsage | None = None, retained_provider_usage: tuple[document_sdk.core.models.ProviderUsage, ...] = (), provider_usage_breakdown: tuple[document_sdk.core.models.ProviderUsage, ...] = (), retained_cloud_execution_attempts: Annotated[tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...], MaxLen(max_length=10000)] = (), cloud_execution_attempts: Annotated[tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...], MaxLen(max_length=10000)] = (), local_ocr_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary | None = None, local_ocr_preprocessing_summary: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingSummary | None = None, azure_fallback_summary: document_sdk.ocr.fallback_models.AzurePageFallbackReport | None = None, retained_azure_fallback_attempts: Annotated[tuple[document_sdk.ocr.fallback_models.AzureFallbackAttemptEvidence, ...], MaxLen(max_length=10000)] = (), azure_fallback_attempt: document_sdk.ocr.fallback_models.AzureFallbackAttemptEvidence | None = None, result: document_sdk.document.models.DocumentAnalysisResult | document_sdk.workflow.models.DocumentWorkflowIntakeResult | None = None) -> None
```

One item outcome retaining exactly one legacy or Workflow payload.

### `BatchItemStatus` (class)

```python
BatchItemStatus(*values)
```

Stable per-item outcome categories.

### `BatchLocalOcrPreprocessingAggregate` (class)

```python
BatchLocalOcrPreprocessingAggregate(*, evaluated_item_count: Annotated[int, Ge(ge=0)] = 0, not_needed_item_count: Annotated[int, Ge(ge=0)] = 0, preprocessing_attempted_item_count: Annotated[int, Ge(ge=0)] = 0, improved_item_count: Annotated[int, Ge(ge=0)] = 0, pass_after_preprocessing_item_count: Annotated[int, Ge(ge=0)] = 0, still_failed_item_count: Annotated[int, Ge(ge=0)] = 0, failed_item_count: Annotated[int, Ge(ge=0)] = 0, page_count: Annotated[int, Ge(ge=0)] = 0, frame_count: Annotated[int, Ge(ge=0)] = 0, attempt_count: Annotated[int, Ge(ge=0)] = 0, preprocessing_pixel_count: Annotated[int, Ge(ge=0)] = 0, extra_operation_count: Annotated[int, Ge(ge=0)] = 0, selected_profile_counts: Annotated[tuple[document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingProfileCount, ...], MaxLen(max_length=4)] = (), safe_failure_counts: Annotated[tuple[document_sdk.document.models.OperationCount, ...], MaxLen(max_length=1)] = ()) -> None
```

Recomputable content-free preprocessing totals across Batch items.

### `BatchLocalOcrQualityAggregate` (class)

```python
BatchLocalOcrQualityAggregate(*, quality_evaluated_item_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, quality_passed_item_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, quality_failed_item_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, quality_not_applicable_item_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, quality_issue_counts: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCount, ...], MaxLen(max_length=8)] = (), recommended_retry_page_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, recommended_retry_frame_count: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0) -> None
```

Content-free Local OCR quality totals across Batch item projections.

### `BatchManifestError` (exception)


Raised when a persisted manifest is invalid or incompatible.

### `BatchManifestItem` (class)

```python
BatchManifestItem(*, input_id: Annotated[str, Strict(strict=True), MinLen(min_length=1), MaxLen(max_length=128), AfterValidator(func=<function _validate_batch_input_id at 0x10bb92ca0>)], relative_name: Annotated[str, MinLen(min_length=1)], status: document_sdk.batch.models.BatchItemStatus, intake_status: document_sdk.workflow.models.DocumentWorkflowIntakeStatus | None = None, duplicate_of: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[Strict(strict=True), MinLen(min_length=1), MaxLen(max_length=128)]), AfterValidator(func=<function _validate_batch_input_id at 0x10bb92ca0>)]] = None, duplicate_identity_kind: Optional[Literal['source_sha256']] = None, issues: tuple[document_sdk.batch.models.BatchItemIssue, ...] = (), source_sha256: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, byte_size: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, consumed_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0, document_type: document_sdk.document.models.DocumentType | None = None, document_format: document_sdk.document.models.DocumentFormat | None = None, pdf_page_count: Annotated[int | None, Strict(strict=True), Ge(ge=1)] = None, excel_worksheet_count: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, image_frame_count: Annotated[int | None, Strict(strict=True), Ge(ge=1)] = None, docx_block_count: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, result_fingerprint: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, resume_eligible_success: bool = False, performed_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), retained_prior_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_usage: document_sdk.core.models.ProviderUsage | None = None, retained_provider_usage: tuple[document_sdk.core.models.ProviderUsage, ...] = (), provider_usage_breakdown: tuple[document_sdk.core.models.ProviderUsage, ...] = (), retained_cloud_execution_attempts: Annotated[tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...], MaxLen(max_length=10000)] = (), cloud_execution_attempts: Annotated[tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...], MaxLen(max_length=10000)] = (), local_ocr_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary | None = None, local_ocr_preprocessing_summary: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingSummary | None = None, azure_fallback_summary: document_sdk.ocr.fallback_models.AzurePageFallbackReport | None = None, retained_azure_fallback_attempts: Annotated[tuple[document_sdk.ocr.fallback_models.AzureFallbackAttemptEvidence, ...], MaxLen(max_length=10000)] = (), azure_fallback_attempt: document_sdk.ocr.fallback_models.AzureFallbackAttemptEvidence | None = None) -> None
```

Content-free resume evidence for one prior input.

### `BatchProcessingLimitError` (exception)


Raised when discovery cannot remain inside a global safety limit.

### `BatchProcessingLimits` (class)

```python
BatchProcessingLimits(*, max_files: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000, max_total_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 5000000000, max_file_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 512000000, max_total_pdf_pages: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_excel_sheets: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_image_frames: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_docx_blocks: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000, max_total_local_ocr_operations: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000, max_total_local_ocr_regions: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000000, max_total_local_ocr_pixels: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000000000, max_total_local_ocr_characters: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000000000, max_total_local_preprocessing_attempts: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 1000000, max_total_local_preprocessing_pixels: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000000000)] = 10000000000, max_total_local_preprocessing_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 1000000, max_total_azure_fallback_pages: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_azure_fallback_frames: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_azure_fallback_inputs: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_azure_fallback_operations: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_azure_fallback_payload_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000000, max_total_paid_operations: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, docx_limits: document_sdk.docx.models.DocxProcessingLimits = <factory>, max_failures: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100, max_workers: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=32)] = 1) -> None
```

Finite batch and cumulative resource limits.

### `BatchProcessingManifest` (class)

```python
BatchProcessingManifest(*, manifest_version: Literal['3'] = '3', sdk_version: Annotated[str, MinLen(min_length=1)], batch_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], processing_options_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], schema_id: str | None = None, schema_version: str | None = None, schema_fingerprint: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, provider_profile_id: str | None = None, items: tuple[document_sdk.batch.models.BatchManifestItem, ...], status_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), performed_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), retained_prior_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_usage_totals: document_sdk.core.models.ProviderUsageTotals = <factory>, local_ocr_quality_aggregate: document_sdk.batch.models.BatchLocalOcrQualityAggregate = <factory>, local_ocr_preprocessing_aggregate: document_sdk.batch.models.BatchLocalOcrPreprocessingAggregate | None = None, azure_fallback_aggregate: document_sdk.batch.models.BatchAzureFallbackAggregate = <factory>, consumed_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0) -> None
```

Serializable safe batch evidence used for compatible resume.

### `BatchProcessingOptions` (class)

```python
BatchProcessingOptions(*, recursive: bool = False, include_hidden: bool = False, include_unsupported: bool = True, deduplicate_sha256: bool = True) -> None
```

Explicit deterministic discovery and processing policy.

### `BatchProcessingResult` (class)

```python
BatchProcessingResult(*, items: tuple[document_sdk.batch.models.BatchItemResult, ...], manifest: document_sdk.batch.models.BatchProcessingManifest, status_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), performed_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), retained_prior_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = (), provider_usage_totals: document_sdk.core.models.ProviderUsageTotals = <factory>, local_ocr_quality_aggregate: document_sdk.batch.models.BatchLocalOcrQualityAggregate = <factory>, local_ocr_preprocessing_aggregate: document_sdk.batch.models.BatchLocalOcrPreprocessingAggregate | None = None, azure_fallback_aggregate: document_sdk.batch.models.BatchAzureFallbackAggregate = <factory>, consumed_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0)] = 0) -> None
```

Complete deterministic batch outcome and its resumable safe manifest.

### `BatchResultValidationError` (exception)


Raised when public Batch evidence is inconsistent.

### `discover_documents` (function)

```python
discover_documents(root: 'Path', *, options: 'BatchProcessingOptions | None' = None, limits: 'BatchProcessingLimits | None' = None) -> 'tuple[BatchDocumentInput, ...]'
```

Discover caller-authorized files in normalized deterministic order.

### `load_batch_manifest` (function)

```python
load_batch_manifest(path: 'Path') -> 'BatchProcessingManifest'
```

Load and validate a safe JSON manifest.

### `process_batch` (function)

```python
process_batch(inputs: 'Iterable[BatchDocumentInput]', *, analysis_options: 'DocumentAnalysisOptions | None' = None, extraction_schema: 'ExtractionSchema | None' = None, ocr_provider: 'OcrProvider | None' = None, azure_fallback_provider: 'object | None' = None, batch_options: 'BatchProcessingOptions | None' = None, limits: 'BatchProcessingLimits | None' = None, resume_manifest: 'BatchProcessingManifest | None' = None, workflow_request: 'DocumentWorkflowRequest | None' = None, workflow_providers: 'DocumentWorkflowProviders | None' = None, workflow_artifact_store: 'WorkflowArtifactStore | None' = None) -> 'BatchProcessingResult'
```

Process inputs with identity-first resume and deduplication decisions.

### `save_batch_manifest` (function)

```python
save_batch_manifest(manifest: 'BatchProcessingManifest', path: 'Path') -> 'None'
```

Atomically persist a safe JSON manifest.

## `document_sdk.core`


### `LOCAL_OCR_QUALITY_ALGORITHM_VERSION` (value)


str(object='') -> str

### `AnalyzedDocument` (class)

```python
AnalyzedDocument(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, document_type: NonEmptyString, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), fields: collections.abc.Mapping[str, document_sdk.core.models.DocumentField] = <factory>) -> None
```

One classified document and its recursively typed fields.

### `BoundingBox` (class)

```python
BoundingBox(*, left: Annotated[float, Ge(ge=0), Le(le=1)], top: Annotated[float, Ge(ge=0), Le(le=1)], right: Annotated[float, Ge(ge=0), Le(le=1)], bottom: Annotated[float, Ge(ge=0), Le(le=1)]) -> None
```

Top-left-origin normalized coordinates within a page.

### `CellWriteRequest` (class)

```python
CellWriteRequest(*, coordinate: NonEmptyString, value: ExcelValue) -> None
```

A value to write to one Excel coordinate.

### `CloudCancellationStatus` (class)

```python
CloudCancellationStatus(*values)
```

Best-effort cancellation outcome without implying billing reversal.

### `CloudExecutionAttemptEvidence` (class)

```python
CloudExecutionAttemptEvidence(*, evidence_version: Literal['cloud-execution-attempt-v3'], provider_name: NonEmptyString, profile_id: NonEmptyString, model_id: NonEmptyString | None = None, api_version: NonEmptyString | None = None, provider_resource_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], status: document_sdk.core.models.CloudExecutionAttemptStatus, logical_operation_count: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=1)] = 1, submitted_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1)] = 0, paid_or_possibly_paid_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1)] = 0, transport_retry_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=0)] = 0, requested_entire_input: bool, requested_pages: tuple[int, ...] = (), requested_frames: tuple[int, ...] = (), submitted_pages: tuple[int, ...] = (), submitted_frames: tuple[int, ...] = (), input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=2000000000)] = 0, cancellation_status: document_sdk.core.models.CloudCancellationStatus = <CloudCancellationStatus.NOT_ATTEMPTED: 'not_attempted'>) -> None
```

Content-free evidence for one attempted cloud execution boundary.

### `CloudExecutionAttemptStatus` (class)

```python
CloudExecutionAttemptStatus(*values)
```

Content-safe lifecycle state for one logical cloud operation.

### `CloudExecutionPolicy` (class)

```python
CloudExecutionPolicy(*, allow_cloud_execution: bool = False, allow_cloud_fallback: bool = False, max_logical_cloud_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_submitted_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_paid_or_possibly_paid_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_pages_or_frames: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=2000000000)] = 0, allow_retry_possibly_paid: bool = False, policy_version: Literal['cloud-execution-policy-v2'] = 'cloud-execution-policy-v2') -> None
```

Provider-neutral, explicitly authorized finite cloud execution policy.

### `CredentialResolutionError` (exception)


Raised when a runtime credential resolver cannot resolve credentials.

### `DependencyNotInstalledError` (exception)


Raised when an optional feature dependency is unavailable.

### `Document` (class)

```python
Document(*, file: document_sdk.core.models.FileDescriptor, pages: tuple[document_sdk.core.models.DocumentPage, ...] = (), tables: tuple[document_sdk.core.models.Table, ...] = (), content_scopes: tuple[document_sdk.core.models.DocumentContentScope, ...] = (), paragraphs: tuple[document_sdk.core.models.DocumentParagraph, ...] = (), key_value_pairs: tuple[document_sdk.core.models.DocumentKeyValuePair, ...] = (), figures: tuple[document_sdk.core.models.DocumentFigure, ...] = (), sections: tuple[document_sdk.core.models.DocumentSection, ...] = (), languages: tuple[document_sdk.core.models.DocumentLanguage, ...] = (), styles: tuple[document_sdk.core.models.DocumentTextStyle, ...] = (), analyzed_documents: tuple[document_sdk.core.models.AnalyzedDocument, ...] = ()) -> None
```

A normalized document with a safe file descriptor.

### `DocumentAddressValue` (class)

```python
DocumentAddressValue(*, house_number: str | None = None, po_box: str | None = None, road: str | None = None, city: str | None = None, state: str | None = None, postal_code: str | None = None, country_region: str | None = None, street_address: str | None = None, unit: str | None = None, city_district: str | None = None, state_district: str | None = None, suburb: str | None = None, house: str | None = None, level: str | None = None) -> None
```

Documented structured address components.

### `DocumentBarcode` (class)

```python
DocumentBarcode(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, kind: NonEmptyString, value: str, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, span: document_sdk.core.models.DocumentSpan) -> None
```

One provider-observed barcode without business interpretation.

### `DocumentCaption` (class)

```python
DocumentCaption(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, content: str, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), elements: tuple[document_sdk.core.models.DocumentElementReference, ...] = ()) -> None
```

Figure or table caption with resolved child references.

### `DocumentContentScope` (class)

```python
DocumentContentScope(*, scope_id: NonEmptyString, content: str, indexed_length: Annotated[int, Ge(ge=0)], string_index_type: Literal['textElements', 'unicodeCodePoint', 'utf16CodeUnit'], origin: Literal['local_native', 'ocr_provider'], page_numbers: tuple[int, ...] = (), frame_numbers: tuple[int, ...] = (), provider_name: NonEmptyString | None = None, profile_id: NonEmptyString | None = None, model_id: NonEmptyString | None = None) -> None
```

One unambiguous processor-owned concatenated-content offset space.

### `DocumentCurrencyValue` (class)

```python
DocumentCurrencyValue(*, amount: decimal.Decimal, currency_code: str | None = None, currency_symbol: str | None = None) -> None
```

A precision-preserving currency value.

### `DocumentElementReference` (class)

```python
DocumentElementReference(*, element_type: Literal['text_block', 'table', 'paragraph', 'key_value_pair', 'figure', 'section', 'analyzed_document'], element_id: NonEmptyString) -> None
```

A provider-independent reference to another mapped document element.

### `DocumentField` (class)

```python
DocumentField(*, sources: tuple[DocumentSourceReference, ...] = (), field_type: NonEmptyString, normalization_status: Optional[Literal['normalized', 'raw_only', 'unsupported_type']] = None, value: str | datetime.date | datetime.time | decimal.Decimal | int | bool | tuple[str, ...] | tuple[document_sdk.core.models.DocumentField, ...] | collections.abc.Mapping[str, document_sdk.core.models.DocumentField] | document_sdk.core.models.DocumentCurrencyValue | document_sdk.core.models.DocumentAddressValue | None = None, content: str | None = None, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), unsupported: bool = False) -> None
```

One strongly typed recursive analyzed-document field.

### `DocumentFigure` (class)

```python
DocumentFigure(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), elements: tuple[document_sdk.core.models.DocumentElementReference, ...] = (), caption: document_sdk.core.models.DocumentCaption | None = None, footnotes: tuple[document_sdk.core.models.DocumentFootnote, ...] = ()) -> None
```

A figure descriptor without downloaded figure image bytes.

### `DocumentFootnote` (class)

```python
DocumentFootnote(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, content: str, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), elements: tuple[document_sdk.core.models.DocumentElementReference, ...] = ()) -> None
```

Figure or table footnote with resolved child references.

### `DocumentFormula` (class)

```python
DocumentFormula(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, kind: NonEmptyString, value: str, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, span: document_sdk.core.models.DocumentSpan) -> None
```

One unevaluated inline or display formula.

### `DocumentKeyValueElement` (class)

```python
DocumentKeyValueElement(*, sources: tuple[DocumentSourceReference, ...] = (), content: str, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = ()) -> None
```

One key or value with complete content evidence.

### `DocumentKeyValuePair` (class)

```python
DocumentKeyValuePair(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, key: document_sdk.core.models.DocumentKeyValueElement, value: document_sdk.core.models.DocumentKeyValueElement | None = None, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = ()) -> None
```

One mapped key and optional value.

### `DocumentLanguage` (class)

```python
DocumentLanguage(*, sources: tuple[DocumentSourceReference, ...] = (), locale: NonEmptyString, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = ()) -> None
```

A detected locale over one or more content spans.

### `DocumentPage` (class)

```python
DocumentPage(*, page_number: Annotated[int, Ge(ge=1)], dimensions: document_sdk.core.models.PageDimensions | None = None, text_blocks: tuple[document_sdk.core.models.TextBlock, ...] = (), tables: tuple[document_sdk.core.models.Table, ...] = (), selection_marks: tuple[document_sdk.core.models.DocumentSelectionMark, ...] = (), barcodes: tuple[document_sdk.core.models.DocumentBarcode, ...] = (), formulas: tuple[document_sdk.core.models.DocumentFormula, ...] = (), content_spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), source: DocumentSourceReference) -> None
```

One normalized document page.

### `DocumentParagraph` (class)

```python
DocumentParagraph(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, content: str, role: str | None = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = ()) -> None
```

Reading-order paragraph and optional semantic role.

### `DocumentProcessingError` (exception)


Raised when document processing fails after input validation.

### `DocumentSdkError` (exception)


Base class for all expected SDK failures.

### `DocumentSection` (class)

```python
DocumentSection(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), elements: tuple[document_sdk.core.models.DocumentElementReference, ...] = ()) -> None
```

A reading-order section with resolved child references.

### `DocumentSelectionMark` (class)

```python
DocumentSelectionMark(*, sources: tuple[DocumentSourceReference, ...] = (), element_id: NonEmptyString, state: Literal['selected', 'unselected'], confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, span: document_sdk.core.models.DocumentSpan) -> None
```

One selected or unselected page mark.

### `DocumentSpan` (class)

```python
DocumentSpan(*, scope_id: NonEmptyString, offset: Annotated[int, Ge(ge=0)], length: Annotated[int, Ge(ge=0)]) -> None
```

A bounded range in one declared document content scope.

### `DocumentTextStyle` (class)

```python
DocumentTextStyle(*, sources: tuple[DocumentSourceReference, ...] = (), is_handwritten: bool | None = None, font_family: str | None = None, font_style: str | None = None, font_weight: str | None = None, foreground_color: str | None = None, background_color: str | None = None, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = ()) -> None
```

Observed text styling over one or more content spans.

### `DocxSourceReference` (class)

```python
DocxSourceReference(*, source_type: Literal['docx'] = 'docx', file_id: NonEmptyString, source_role: Literal['story', 'section', 'custom_property'] = 'story', package_part: NonEmptyString | None = None, story_type: NonEmptyString, story_id: NonEmptyString, block_index: Annotated[int, Ge(ge=0)], paragraph_index: Annotated[int | None, Ge(ge=0)] = None, run_index: Annotated[int | None, Ge(ge=0)] = None, table_index: Annotated[int | None, Ge(ge=0)] = None, table_path: tuple[typing.Annotated[int, FieldInfo(annotation=NoneType, required=True, metadata=[Ge(ge=0)])], ...] = (), row_index: Annotated[int | None, Ge(ge=0)] = None, cell_index: Annotated[int | None, Ge(ge=0)] = None, character_start: Annotated[int | None, Ge(ge=0)] = None, character_end: Annotated[int | None, Ge(ge=0)] = None, resource_id: NonEmptyString | None = None) -> None
```

A structural location in one DOCX story without fabricated pagination.

### `EncryptedDocumentError` (exception)


Raised when an encrypted document cannot be processed.

### `ExcelCell` (class)

```python
ExcelCell(*, coordinate: NonEmptyString, value: ExcelValue = None, formula: str | None = None, formula_text: str | None = None, cached_value: ExcelValue = None, has_cached_value: bool = False, cache_available: bool = False, formula_kind: Optional[Literal['ordinary', 'shared', 'array', 'dynamic_array']] = None, external_reference: bool = False, requires_recalculation: bool = False, data_type: NonEmptyString, style_id: Annotated[int | None, Ge(ge=0)] = None, number_format: str | None = None, source: document_sdk.core.models.ExcelSourceReference, temporal_source: document_sdk.core.models.ExcelTemporalSource | None = None) -> None
```

A normalized Excel cell that distinguishes values and formulas.

### `ExcelCellLimitExceededError` (exception)

```python
ExcelCellLimitExceededError(*, requested_cells: 'int', max_cells: 'int') -> 'None'
```

Raised before an Excel read would exceed its configured cell limit.

### `ExcelSourceReference` (class)

```python
ExcelSourceReference(*, source_type: Literal['excel'] = 'excel', file_id: NonEmptyString, sheet_name: WorksheetName, cell_range: NonEmptyString) -> None
```

A sheet and cell or range location in an Excel workbook.

### `ExcelTemporalSource` (class)

```python
ExcelTemporalSource(*, kind: Literal['excel_serial', 'iso8601'], raw_value: str, date_system: Optional[Literal['1900', '1904']] = None, origin: Literal['value', 'formula_cache']) -> None
```

Caller-declared temporal source text, separate from normalized values.

### `FileAccessError` (exception)


Raised when a local file cannot be accessed safely.

### `FileDescriptor` (class)

```python
FileDescriptor(*, file_id: NonEmptyString, filename: NonEmptyString, extension: str, mime_type: NonEmptyString, size_bytes: Annotated[int, Ge(ge=0)], fingerprint: document_sdk.core.models.FileFingerprint) -> None
```

Safe file metadata that deliberately excludes the local path.

### `FileFingerprint` (class)

```python
FileFingerprint(*, algorithm: Literal['sha256'] = 'sha256', value: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')]) -> None
```

A stable cryptographic fingerprint for file contents.

### `ImageFrameInspection` (class)

```python
ImageFrameInspection(*, frame_number: Annotated[int, Ge(ge=1)], width: Annotated[int, Gt(gt=0)], height: Annotated[int, Gt(gt=0)], mode: NonEmptyString, pixel_count: Annotated[int, Gt(gt=0)], has_alpha: bool, exif_orientation: Optional[Annotated[int, FieldInfo(annotation=NoneType, required=True, metadata=[Ge(ge=1), Le(le=8)])]] = None, decode_verified: bool, source: document_sdk.core.models.ImageSourceReference) -> None
```

Normalized facts for one encoded image frame.

### `ImageInspection` (class)

```python
ImageInspection(*, file: document_sdk.core.models.FileDescriptor, format: Literal['PNG', 'JPEG', 'TIFF', 'BMP', 'WEBP'], mime_type: Literal['image/png', 'image/jpeg', 'image/tiff', 'image/bmp', 'image/webp'], frame_count: Annotated[int, Ge(ge=1)], animated: bool, frames: Annotated[tuple[document_sdk.core.models.ImageFrameInspection, ...], MinLen(min_length=1)], warnings: tuple[NonEmptyString, ...] = ()) -> None
```

Local image inspection facts without Pillow-owned objects.

### `ImageLimitExceededError` (exception)

```python
ImageLimitExceededError(*, limit_name: 'str', observed: 'int', maximum: 'int') -> 'None'
```

Raised before image decoding would exceed a configured limit.

### `ImageProcessingError` (exception)


Raised when local image inspection cannot complete safely.

### `ImageProcessingLimits` (class)

```python
ImageProcessingLimits(*, max_frames: Annotated[int, Gt(gt=0)] = 100, max_pixels_per_frame: Annotated[int, Gt(gt=0)] = 25000000, max_total_pixels: Annotated[int, Gt(gt=0)] = 100000000, max_working_pixels: Annotated[int, Gt(gt=0)] = 50000000, max_output_bytes: Annotated[int, Gt(gt=0)] = 50000000, max_output_width: Annotated[int, Gt(gt=0)] = 20000, max_output_height: Annotated[int, Gt(gt=0)] = 20000) -> None
```

Explicit bounds applied before full image-frame decoding.

### `ImageSourceReference` (class)

```python
ImageSourceReference(*, source_type: Literal['image'] = 'image', file_id: NonEmptyString, frame_number: Annotated[int, Ge(ge=1)], bounding_box: document_sdk.core.models.BoundingBox | None = None) -> None
```

A location in an image using a one-based frame number.

### `InvalidSourceReferenceError` (exception)


Raised when source information cannot identify a valid origin.

### `LocalOcrInputQualityAssessment` (class)

```python
LocalOcrInputQualityAssessment(*, assessment_id: Annotated[str, _PydanticGeneralMetadata(pattern='^(pdf|image):[1-9][0-9]*$')], source_kind: Literal['pdf', 'image'], source_index: Annotated[int, Ge(ge=1)], character_count: Annotated[int, Ge(ge=0)], region_count: Annotated[int, Ge(ge=0)], confidence_weighted_character_count: Annotated[int, Ge(ge=0)], low_confidence_character_count: Annotated[int, Ge(ge=0)], suspicious_character_count: Annotated[int, Ge(ge=0)], region_area_numerator: Annotated[int, Ge(ge=0)], region_area_denominator: Annotated[int, Gt(gt=0)], mean_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, low_confidence_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, suspicious_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, region_area_ratio: Annotated[float, Ge(ge=0), Le(le=1)], decision: document_sdk.core.local_ocr_quality.LocalOcrQualityDecision, issue_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=6)] = ()) -> None
```

Content-free quality evidence for one submitted Local OCR input.

### `LocalOcrIntrinsicQualityPolicy` (class)

```python
LocalOcrIntrinsicQualityPolicy(*, minimum_characters_per_input: Annotated[int | None, Ge(ge=0)] = None, minimum_mean_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, low_confidence_threshold: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, maximum_low_confidence_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, maximum_suspicious_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, minimum_region_area_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, include_private_use_characters: bool = False) -> None
```

Explicit intrinsic rules; optional thresholds are disabled by default.

### `LocalOcrQualityDecision` (class)

```python
LocalOcrQualityDecision(*values)
```

Provider-neutral decision for explicitly enabled Local OCR quality.

### `LocalOcrQualityIssueCode` (class)

```python
LocalOcrQualityIssueCode(*values)
```

Stable content-free Local OCR quality issue categories.

### `LocalOcrQualityIssueCount` (class)

```python
LocalOcrQualityIssueCount(*, code: document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, count: Annotated[int, Gt(gt=0)]) -> None
```

One deterministic non-zero issue-category count.

### `LocalOcrQualityPolicy` (class)

```python
LocalOcrQualityPolicy(*, intrinsic: document_sdk.core.local_ocr_quality.LocalOcrIntrinsicQualityPolicy = <factory>, structured: document_sdk.core.local_ocr_quality.LocalOcrStructuredQualityPolicy | None = None) -> None
```

Complete auditable Local OCR quality policy used by one report.

### `LocalOcrQualityReport` (class)

```python
LocalOcrQualityReport(*, algorithm_version: Literal['local-ocr-quality-v1'] = 'local-ocr-quality-v1', policy: document_sdk.core.local_ocr_quality.LocalOcrQualityPolicy, input_assessments: tuple[document_sdk.core.local_ocr_quality.LocalOcrInputQualityAssessment, ...] = (), structural_issue_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=2)] = (), required_field_count: Annotated[int, Ge(ge=0)] = 0, missing_required_field_count: Annotated[int, Ge(ge=0)] = 0, ambiguous_required_field_count: Annotated[int, Ge(ge=0)] = 0, constrained_required_field_issue_count: Annotated[int, Ge(ge=0)] = 0, table_count: Annotated[int, Ge(ge=0)] = 0, table_cell_count: Annotated[int, Ge(ge=0)] = 0, empty_table_cell_count: Annotated[int, Ge(ge=0)] = 0, summary_evidence: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary) -> None
```

Complete explicit Local OCR quality report without recognized content.

### `LocalOcrQualitySummary` (class)

```python
LocalOcrQualitySummary(*, algorithm_version: Literal['local-ocr-quality-v1'] = 'local-ocr-quality-v1', policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], decision: document_sdk.core.local_ocr_quality.LocalOcrQualityDecision, evaluated_input_count: Annotated[int, Ge(ge=0)], passed_input_count: Annotated[int, Ge(ge=0)], failed_input_count: Annotated[int, Ge(ge=0)], evaluated_pages: tuple[int, ...] = (), evaluated_frames: tuple[int, ...] = (), issue_counts_by_code: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCount, ...], MaxLen(max_length=8)] = (), reason_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=8)] = (), failed_pages: tuple[int, ...] = (), failed_frames: tuple[int, ...] = (), retry_recommended: bool = False, recommended_retry_pages: tuple[int, ...] = (), recommended_retry_frames: tuple[int, ...] = (), character_count: Annotated[int, Ge(ge=0)], region_count: Annotated[int, Ge(ge=0)], confidence_weighted_character_count: Annotated[int, Ge(ge=0)], low_confidence_character_count: Annotated[int, Ge(ge=0)], suspicious_character_count: Annotated[int, Ge(ge=0)], region_area_numerator: Annotated[int, Ge(ge=0)], region_area_denominator: Annotated[int, Ge(ge=0)], required_field_count: Annotated[int, Ge(ge=0)], missing_required_field_count: Annotated[int, Ge(ge=0)], ambiguous_required_field_count: Annotated[int, Ge(ge=0)], constrained_required_field_issue_count: Annotated[int, Ge(ge=0)], table_count: Annotated[int, Ge(ge=0)], table_cell_count: Annotated[int, Ge(ge=0)], empty_table_cell_count: Annotated[int, Ge(ge=0)]) -> None
```

Content-free durable projection suitable for manifests and Resume.

### `LocalOcrStructuredQualityPolicy` (class)

```python
LocalOcrStructuredQualityPolicy(*, maximum_missing_required_fields: Annotated[int | None, Ge(ge=0)] = None, minimum_table_count: Annotated[int | None, Ge(ge=0)] = None, maximum_empty_table_cell_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None) -> None
```

Explicit Structured Extraction and table-completeness quality rules.

### `PageDimensions` (class)

```python
PageDimensions(*, width: Annotated[float, Gt(gt=0)], height: Annotated[float, Gt(gt=0)], unit: Literal['points', 'pixels'] = 'points', rotation: Literal[0, 90, 180, 270] = 0, angle_degrees: Annotated[float | None, Ge(ge=-180), Le(le=180)] = None) -> None
```

Original page geometry and clockwise rotation.

### `PdfInspection` (class)

```python
PdfInspection(*, file: document_sdk.core.models.FileDescriptor, page_count: Annotated[int, Ge(ge=1)], encrypted: bool, has_text_layer: bool, scanned_pdf_candidate: bool, native_text_page_numbers: tuple[int, ...], ocr_candidate_page_numbers: tuple[int, ...], fully_scanned: bool, partially_scanned: bool, pages: tuple[document_sdk.core.models.PdfPageInspection, ...], file_size_within_limit: bool = True, page_count_within_limit: bool = True, largest_page_width_points: Annotated[float, Ge(ge=0)] = 0, largest_page_height_points: Annotated[float, Ge(ge=0)] = 0, largest_page_area_points: Annotated[float, Ge(ge=0)] = 0) -> None
```

Local PDF inspection facts.

### `PdfPageInspection` (class)

```python
PdfPageInspection(*, page_number: Annotated[int, Ge(ge=1)], dimensions: document_sdk.core.models.PageDimensions, has_text_layer: bool, native_text_character_count: Annotated[int, Ge(ge=0)], ocr_candidate: bool, source: document_sdk.core.models.PdfSourceReference) -> None
```

Inspection facts for one PDF page.

### `PdfSourceReference` (class)

```python
PdfSourceReference(*, source_type: Literal['pdf'] = 'pdf', file_id: NonEmptyString, page_number: Annotated[int, Ge(ge=1)], bounding_box: document_sdk.core.models.BoundingBox | None = None) -> None
```

A location in a PDF using a one-based page number.

### `ProcessingError` (class)

```python
ProcessingError(*, code: Annotated[str, MinLen(min_length=1)], message: Annotated[str, MinLen(min_length=1)], retryable: bool = False, source: SourceReference | None = None) -> None
```

A normalized processing failure description.

### `ProcessingMetadata` (class)

```python
ProcessingMetadata(*, operation: Annotated[str, MinLen(min_length=1)], provider_name: str | None = None, profile_id: str | None = None, model_id: str | None = None, provider_usage: document_sdk.core.models.ProviderUsage | None = None, cloud_execution_attempt: document_sdk.core.models.CloudExecutionAttemptEvidence | None = None, local_ocr_quality_report: document_sdk.core.local_ocr_quality.LocalOcrQualityReport | None = None, local_ocr_preprocessing_report: typing.Any | None = None, duration_ms: Annotated[float | None, Ge(ge=0)] = None, attributes: collections.abc.Mapping[str, JsonValue] = <factory>) -> None
```

Safe operational metadata that excludes runtime credentials.

### `ProcessingResult` (class)

```python
ProcessingResult(*, data: Optional[ResultT] = None, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = (), errors: tuple[document_sdk.core.results.ProcessingError, ...] = (), metadata: document_sdk.core.results.ProcessingMetadata) -> None
```

A normalized generic result with warnings, errors, and metadata.

### `ProcessingWarning` (class)

```python
ProcessingWarning(*, code: Annotated[str, MinLen(min_length=1)], message: Annotated[str, MinLen(min_length=1)], source: SourceReference | None = None, category: Annotated[str | None, MinLen(min_length=1)] = None, count: Annotated[int | None, Ge(ge=1)] = None) -> None
```

A non-fatal processing condition.

### `ProviderAuthenticationError` (exception)

```python
ProviderAuthenticationError(message: 'str', *, status_code: 'int' = 401, error_code: 'str | None' = None) -> 'None'
```

Raised when a provider rejects the resolved authentication.

### `ProviderAuthorizationError` (exception)

```python
ProviderAuthorizationError(message: 'str', *, status_code: 'int' = 403, error_code: 'str | None' = None) -> 'None'
```

Raised when the resolved identity cannot perform the operation.

### `ProviderConfigurationError` (exception)


Raised when provider configuration is invalid for an operation.

### `ProviderRateLimitError` (exception)

```python
ProviderRateLimitError(message: 'str', *, status_code: 'int' = 429, error_code: 'str | None' = None) -> 'None'
```

Raised when a provider rate limit temporarily rejects work.

### `ProviderRequestError` (exception)

```python
ProviderRequestError(message: 'str', *, status_code: 'int', error_code: 'str | None' = None) -> 'None'
```

Raised when a provider rejects a non-authentication request.

### `ProviderResponseError` (exception)

```python
ProviderResponseError(message: 'str') -> 'None'
```

Raised when a provider returns malformed or unsafe result data.

### `ProviderTimeoutError` (exception)

```python
ProviderTimeoutError(message: 'str') -> 'None'
```

Raised when a provider operation exceeds its configured wait.

### `ProviderUnavailableError` (exception)

```python
ProviderUnavailableError(message: 'str', *, status_code: 'int | None' = None, error_code: 'str | None' = None, retryable: 'bool' = True) -> 'None'
```

Raised when an explicitly selected provider cannot be reached or used.

### `ProviderUsage` (class)

```python
ProviderUsage(*, provider_name: NonEmptyString, profile_id: NonEmptyString, model_id: NonEmptyString | None = None, api_version: NonEmptyString | None = None, provider_resource_identity: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, submitted_pages: tuple[int, ...] = (), returned_pages: tuple[int, ...] = (), submitted_frames: tuple[int, ...] = (), returned_frames: tuple[int, ...] = (), requested_features: tuple[NonEmptyString, ...] = (), query_field_count: Annotated[int, Ge(ge=0)] = 0, local_operation_count: Annotated[int, Ge(ge=0)] = 0, local_page_count: Annotated[int, Ge(ge=0)] = 0, local_frame_count: Annotated[int, Ge(ge=0)] = 0, local_region_count: Annotated[int, Ge(ge=0)] = 0, local_attempted_region_count: Annotated[int, Ge(ge=0)] = 0, local_input_pixel_count: Annotated[int, Ge(ge=0)] = 0, local_output_character_count: Annotated[int, Ge(ge=0)] = 0, local_attempted_output_character_count: Annotated[int, Ge(ge=0)] = 0, local_preprocessing_attempt_count: Annotated[int, Ge(ge=0)] = 0, local_preprocessing_operation_count: Annotated[int, Ge(ge=0)] = 0, local_preprocessing_pixel_count: Annotated[int, Ge(ge=0)] = 0, azure_operation_count: Annotated[int, Ge(ge=0)] = 0, paid_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_logical_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_submitted_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_paid_or_possibly_paid_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_transport_retry_count: Annotated[int, Ge(ge=0)] = 0) -> None
```

Safe structured evidence for one explicit Provider operation.

### `ProviderUsageTotals` (class)

```python
ProviderUsageTotals(*, local_operation_count: Annotated[int, Ge(ge=0)] = 0, local_page_count: Annotated[int, Ge(ge=0)] = 0, local_frame_count: Annotated[int, Ge(ge=0)] = 0, local_region_count: Annotated[int, Ge(ge=0)] = 0, local_attempted_region_count: Annotated[int, Ge(ge=0)] = 0, local_input_pixel_count: Annotated[int, Ge(ge=0)] = 0, local_output_character_count: Annotated[int, Ge(ge=0)] = 0, local_attempted_output_character_count: Annotated[int, Ge(ge=0)] = 0, local_preprocessing_attempt_count: Annotated[int, Ge(ge=0)] = 0, local_preprocessing_operation_count: Annotated[int, Ge(ge=0)] = 0, local_preprocessing_pixel_count: Annotated[int, Ge(ge=0)] = 0, azure_operation_count: Annotated[int, Ge(ge=0)] = 0, paid_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_logical_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_submitted_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_paid_or_possibly_paid_operation_count: Annotated[int, Ge(ge=0)] = 0, cloud_transport_retry_count: Annotated[int, Ge(ge=0)] = 0) -> None
```

Content-free aggregate Provider operation evidence for Batch manifests.

### `RenderedPage` (class)

```python
RenderedPage(*, image_bytes: bytes, content_type: Literal['image/png'] = 'image/png', width_pixels: Annotated[int, Gt(gt=0)], height_pixels: Annotated[int, Gt(gt=0)], dpi: Annotated[int, Gt(gt=0)], source: document_sdk.core.models.PdfSourceReference) -> None
```

A rendered page or page region backed by encoded image bytes.

### `SheetWriteRequest` (class)

```python
SheetWriteRequest(*, name: NonEmptyString, cells: tuple[document_sdk.core.models.CellWriteRequest, ...] = ()) -> None
```

One worksheet to create in a workbook.

### `SourceReference` (value)


Type alias.

### `Table` (class)

```python
Table(*, cells: tuple[document_sdk.core.models.TableCell, ...] = (), source: SourceReference, row_count: Annotated[int | None, Ge(ge=1)] = None, column_count: Annotated[int | None, Ge(ge=1)] = None, element_id: NonEmptyString | None = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), sources: tuple[SourceReference, ...] = (), caption: document_sdk.core.models.DocumentCaption | None = None, footnotes: tuple[document_sdk.core.models.DocumentFootnote, ...] = ()) -> None
```

A normalized collection of table cells.

### `TableCell` (class)

```python
TableCell(*, row: Annotated[int, Ge(ge=1)], column: Annotated[int, Ge(ge=1)], row_span: Annotated[int, Ge(ge=1)] = 1, column_span: Annotated[int, Ge(ge=1)] = 1, text: str, source: SourceReference, kind: NonEmptyString | None = None, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = (), sources: tuple[SourceReference, ...] = (), elements: tuple[document_sdk.core.models.DocumentElementReference, ...] = ()) -> None
```

A normalized table cell with one-based row and column indices.

### `TextBlock` (class)

```python
TextBlock(*, text: str, source: SourceReference, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, element_id: NonEmptyString | None = None, spans: tuple[document_sdk.core.models.DocumentSpan, ...] = ()) -> None
```

A text fragment with its original document location.

### `UnsupportedFileError` (exception)


Raised when a file type is outside an API's supported formats.

### `WorkbookInspection` (class)

```python
WorkbookInspection(*, file: document_sdk.core.models.FileDescriptor, sheet_names: tuple[WorksheetName, ...], worksheets: tuple[document_sdk.core.models.WorksheetInspection, ...]) -> None
```

Local workbook structure and safe file metadata.

### `WorkbookWriteRequest` (class)

```python
WorkbookWriteRequest(*, sheets: Annotated[tuple[document_sdk.core.models.SheetWriteRequest, ...], MinLen(min_length=1)]) -> None
```

A complete local workbook creation request.

### `WorksheetData` (class)

```python
WorksheetData(*, file: document_sdk.core.models.FileDescriptor, sheet_name: WorksheetName, used_range: str | None, cells: tuple[document_sdk.core.models.ExcelCell, ...] = ()) -> None
```

Normalized cell data from one worksheet.

### `WorksheetInspection` (class)

```python
WorksheetInspection(*, name: WorksheetName, used_range: str | None, max_row: Annotated[int, Ge(ge=0), Le(le=1048576)], max_column: Annotated[int, Ge(ge=0), Le(le=16384)], merged_ranges: tuple[str, ...] = (), hidden_rows: tuple[int, ...] = (), hidden_columns: tuple[str, ...] = (), formula_cell_count: Annotated[int, Ge(ge=0)]) -> None
```

Workbook structure facts for one worksheet.

## `document_sdk.document`


### `DocumentAnalysisOptions` (class)

```python
DocumentAnalysisOptions(*, pdf_mode: document_sdk.document.models.PdfAnalysisMode = <PdfAnalysisMode.NATIVE: 'native'>, hybrid_pdf_options: document_sdk.pipeline.models.HybridPdfAnalysisOptions | None = None, structured_extraction_options: document_sdk.extraction.models.StructuredExtractionOptions | None = None, docx_options: document_sdk.docx.models.DocxAnalysisOptions | None = None, azure_fallback_policy: document_sdk.ocr.fallback_models.AzurePageFallbackPolicy | None = None) -> None
```

Cost-safe explicit unified analysis options.

### `DocumentAnalysisResult` (class)

```python
DocumentAnalysisResult(*, envelope: document_sdk.document.models.DocumentEnvelope, inspection: document_sdk.document.models.DocumentInspectionResult, analysis: document_sdk.document.models.PdfDocumentAnalysis | document_sdk.document.models.ExcelDocumentAnalysis | document_sdk.document.models.ImageDocumentAnalysis | document_sdk.document.models.DocxDocumentAnalysis, structured_extraction: document_sdk.extraction.models.StructuredExtractionResult | None = None, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = (), issues: tuple[document_sdk.core.results.ProcessingError, ...] = (), provider_usage: document_sdk.core.models.ProviderUsage | None = None, local_ocr_quality_report: document_sdk.core.local_ocr_quality.LocalOcrQualityReport | None = None, local_ocr_preprocessing_report: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingReport | None = None, azure_fallback_report: document_sdk.ocr.fallback_models.AzurePageFallbackReport | None = None, provider_usage_breakdown: tuple[document_sdk.core.models.ProviderUsage, ...] = (), cloud_execution_attempts: tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...] = (), processing_manifest: document_sdk.document.models.DocumentProcessingManifest) -> None
```

Unified analysis result preserving detailed family-specific evidence.

### `DocumentEnvelope` (class)

```python
DocumentEnvelope(*, document_type: document_sdk.document.models.DocumentType, document_format: document_sdk.document.models.DocumentFormat, media_type: Annotated[str, MinLen(min_length=1)], source_name: Annotated[str, MinLen(min_length=1)], sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], byte_size: Annotated[int, Strict(strict=True), Ge(ge=0)], sdk_version: Annotated[str, MinLen(min_length=1)], extension_mismatch: bool = False) -> None
```

Safe immutable identity for the exact processed bytes.

### `DocumentFormat` (class)

```python
DocumentFormat(*values)
```

Supported concrete content formats.

### `DocumentInspectionResult` (class)

```python
DocumentInspectionResult(*, envelope: document_sdk.document.models.DocumentEnvelope, inspection: document_sdk.document.models.PdfDocumentInspection | document_sdk.document.models.ExcelDocumentInspection | document_sdk.document.models.ImageDocumentInspection | document_sdk.document.models.DocxDocumentInspection, pdf_page_count: Annotated[int | None, Strict(strict=True), Ge(ge=1)] = None, excel_worksheet_count: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, image_frame_count: Annotated[int | None, Strict(strict=True), Ge(ge=1)] = None, docx_block_count: Annotated[int | None, Strict(strict=True), Ge(ge=0)] = None, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = ()) -> None
```

Unified inspection result without backend objects or paths.

### `DocumentProcessingManifest` (class)

```python
DocumentProcessingManifest(*, manifest_version: Literal['3'] = '3', source_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], sdk_version: Annotated[str, MinLen(min_length=1)], document_type: document_sdk.document.models.DocumentType, document_format: document_sdk.document.models.DocumentFormat, processing_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], schema_id: str | None = None, schema_version: str | None = None, schema_fingerprint: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, provider_profile_id: str | None = None, provider_usage: document_sdk.core.models.ProviderUsage | None = None, provider_usage_breakdown: tuple[document_sdk.core.models.ProviderUsage, ...] = (), cloud_execution_attempts: tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...] = (), local_ocr_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary | None = None, local_ocr_preprocessing_summary: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingSummary | None = None, azure_fallback_summary: document_sdk.ocr.fallback_models.AzurePageFallbackReport | None = None, azure_fallback_policy_fingerprint: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, operation_counts: tuple[document_sdk.document.models.OperationCount, ...] = ()) -> None
```

Content-free processing evidence for one document operation.

### `DocumentResultValidationError` (exception)


Raised when public Unified Document evidence is inconsistent.

### `DocumentSourceChangedError` (exception)


Raised when source bytes change during one document operation.

### `DocumentType` (class)

```python
DocumentType(*values)
```

Supported high-level document families.

### `DocumentTypeDetection` (class)

```python
DocumentTypeDetection(*, envelope: document_sdk.document.models.DocumentEnvelope, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = ()) -> None
```

Content-derived type detection with safe warnings.

### `DocumentTypeMismatchError` (exception)


Raised when a requested operation is incompatible with the content.

### `DocxDocumentAnalysis` (class)

```python
DocxDocumentAnalysis(*, kind: Literal['word'] = 'word', docx: document_sdk.docx.models.DocxAnalysisResult) -> None
```

Typed DOCX analysis retaining structure and normalized Document.

### `DocxDocumentInspection` (class)

```python
DocxDocumentInspection(*, kind: Literal['word'] = 'word', inspection: document_sdk.docx.models.DocxInspection) -> None
```

Typed DOCX inspection payload.

### `ExcelDocumentAnalysis` (class)

```python
ExcelDocumentAnalysis(*, kind: Literal['excel'] = 'excel', workbook: document_sdk.core.models.WorkbookInspection) -> None
```

Typed Excel analysis retaining its native workbook inspection.

### `ImageDocumentAnalysis` (class)

```python
ImageDocumentAnalysis(*, kind: Literal['image'] = 'image', image: document_sdk.core.models.ImageInspection, ocr_result: document_sdk.core.results.ProcessingResult[Document] | None = None) -> None
```

Typed image analysis with optional explicit OCR result.

### `PdfDocumentAnalysis` (class)

```python
PdfDocumentAnalysis(*, kind: Literal['pdf'] = 'pdf', document: document_sdk.core.models.Document, processing_result: document_sdk.core.results.ProcessingResult[Document] | None = None) -> None
```

Typed PDF analysis retaining the complete existing result.

### `UnsupportedDocumentOperationError` (exception)


Raised when a document family cannot perform a requested operation.

### `UnsupportedDocumentTypeError` (exception)


Raised when content is not one of the supported document families.

### `analyze_document` (function)

```python
analyze_document(path: 'Path', *, options: 'DocumentAnalysisOptions | None' = None, extraction_schema: 'ExtractionSchema | None' = None, ocr_provider: 'OcrProvider | None' = None, azure_fallback_provider: 'object | None' = None, limits: 'object | None' = None) -> 'DocumentAnalysisResult'
```

Analyze one supported document with local and Provider use kept explicit.

### `detect_document_type` (function)

```python
detect_document_type(path: 'Path') -> 'DocumentTypeDetection'
```

Detect and validate PDF, OOXML spreadsheet, or image content.

### `inspect_document` (function)

```python
inspect_document(path: 'Path', *, limits: 'object | None' = None) -> 'DocumentInspectionResult'
```

Inspect a detected family through its existing public inspection API.

## `document_sdk.docx`


### `DocxAnalysisOptions` (class)

```python
DocxAnalysisOptions(*, revision_view: document_sdk.docx.models.DocxRevisionView = <DocxRevisionView.CURRENT: 'current'>, include_headers: bool = True, include_footers: bool = True, include_comments: bool = True, include_footnotes: bool = True, include_endnotes: bool = True, include_custom_properties_as_key_values: bool = True, extract_two_column_key_value_tables: bool = False) -> None
```

Explicit local DOCX projection and candidate-extraction policy.

### `DocxAnalysisResult` (class)

```python
DocxAnalysisResult(*, inspection: document_sdk.docx.models.DocxInspection, structure: document_sdk.docx.models.DocxDocumentStructure, document: document_sdk.core.models.Document, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = (), issues: tuple[document_sdk.core.results.ProcessingError, ...] = (), processing_manifest: document_sdk.docx.models.DocxProcessingManifest) -> None
```

Complete provider-independent DOCX analysis.

### `DocxBlock` (value)


Runtime representation of an annotated type.

### `DocxBookmark` (class)

```python
DocxBookmark(*, bookmark_id: Annotated[str, MinLen(min_length=1)], name: str | None = None, start_source: document_sdk.core.models.DocxSourceReference, end_source: document_sdk.core.models.DocxSourceReference | None = None) -> None
```

A Word bookmark range marker.

### `DocxComment` (class)

```python
DocxComment(*, comment_id: Annotated[str, MinLen(min_length=1)], author: str | None = None, initials: str | None = None, created_at: datetime.datetime | None = None, blocks: tuple[typing.Annotated[document_sdk.docx.models.DocxParagraph | document_sdk.docx.models.DocxTable, FieldInfo(annotation=NoneType, required=True, discriminator='kind')], ...] = (), range_start: document_sdk.core.models.DocxSourceReference | None = None, range_end: document_sdk.core.models.DocxSourceReference | None = None, reference: document_sdk.core.models.DocxSourceReference | None = None, source: document_sdk.core.models.DocxSourceReference) -> None
```

One comment definition and available anchor evidence.

### `DocxContentControl` (class)

```python
DocxContentControl(*, control_id: Annotated[str, MinLen(min_length=1)], sdt_id: str | None = None, tag: str | None = None, alias: str | None = None, control_type: Annotated[str, MinLen(min_length=1)], lock_state: str | None = None, placeholder: bool = False, list_values: tuple[str, ...] = (), selected_value: str | None = None, value: str | bool | datetime.date | None = None, blocks: tuple[typing.Annotated[document_sdk.docx.models.DocxParagraph | document_sdk.docx.models.DocxTable, FieldInfo(annotation=NoneType, required=True, discriminator='kind')], ...] = (), source: document_sdk.core.models.DocxSourceReference) -> None
```

One read-only Structured Document Tag and deterministic typed value.

### `DocxDocumentProperties` (class)

```python
DocxDocumentProperties(*, title: str | None = None, subject: str | None = None, creator: str | None = None, keywords: str | None = None, description: str | None = None, last_modified_by: str | None = None, created_at: datetime.datetime | None = None, modified_at: datetime.datetime | None = None, application: str | None = None, company: str | None = None, declared_page_count: Annotated[int | None, Ge(ge=0)] = None, declared_page_count_is_authoritative: Literal[False] = False, custom_properties: tuple[document_sdk.docx.models.DocxCustomProperty, ...] = ()) -> None
```

Safe core, extended, and custom document properties.

### `DocxDocumentStructure` (class)

```python
DocxDocumentStructure(*, stories: tuple[document_sdk.docx.models.DocxStory, ...], sections: tuple[document_sdk.docx.models.DocxSection, ...] = (), comments: tuple[document_sdk.docx.models.DocxComment, ...] = (), footnotes: tuple[document_sdk.docx.models.DocxFootnote, ...] = (), endnotes: tuple[document_sdk.docx.models.DocxEndnote, ...] = (), content_controls: tuple[document_sdk.docx.models.DocxContentControl, ...] = (), hyperlinks: tuple[document_sdk.docx.models.DocxHyperlink, ...] = (), bookmarks: tuple[document_sdk.docx.models.DocxBookmark, ...] = (), embedded_resources: tuple[document_sdk.docx.models.DocxEmbeddedResource, ...] = (), track_changes: document_sdk.docx.models.DocxTrackChangesSummary = <factory>) -> None
```

Complete ordered DOCX stories and cross-story evidence.

### `DocxEmbeddedResource` (class)

```python
DocxEmbeddedResource(*, resource_id: Annotated[str, MinLen(min_length=1)], relationship_role: Annotated[str, MinLen(min_length=1)], resource_type: Annotated[str, MinLen(min_length=1)], content_type: str | None = None, safe_basename: str | None = None, byte_size: Annotated[int | None, Ge(ge=0)] = None, sha256: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, internal: bool, alt_text: str | None = None, title: str | None = None, description: str | None = None) -> None
```

Opaque internal or external resource inventory without bytes.

### `DocxEndnote` (class)

```python
DocxEndnote(*, note_id: Annotated[str, MinLen(min_length=1)], blocks: tuple[typing.Annotated[document_sdk.docx.models.DocxParagraph | document_sdk.docx.models.DocxTable, FieldInfo(annotation=NoneType, required=True, discriminator='kind')], ...] = (), reference_sources: tuple[document_sdk.core.models.DocxSourceReference, ...] = (), source: document_sdk.core.models.DocxSourceReference) -> None
```

One user endnote story.

### `DocxFootnote` (class)

```python
DocxFootnote(*, note_id: Annotated[str, MinLen(min_length=1)], blocks: tuple[typing.Annotated[document_sdk.docx.models.DocxParagraph | document_sdk.docx.models.DocxTable, FieldInfo(annotation=NoneType, required=True, discriminator='kind')], ...] = (), reference_sources: tuple[document_sdk.core.models.DocxSourceReference, ...] = (), source: document_sdk.core.models.DocxSourceReference) -> None
```

One user footnote story.

### `DocxHyperlink` (class)

```python
DocxHyperlink(*, hyperlink_id: Annotated[str, MinLen(min_length=1)], display_text: str, target: str | None = None, anchor: str | None = None, tooltip: str | None = None, history: bool | None = None, external: bool = False, source: document_sdk.core.models.DocxSourceReference) -> None
```

Internal or external hyperlink evidence that is never followed.

### `DocxInspection` (class)

```python
DocxInspection(*, file: document_sdk.core.models.FileDescriptor, package: document_sdk.docx.models.DocxPackageSummary, properties: document_sdk.docx.models.DocxDocumentProperties, block_count: Annotated[int, Ge(ge=0)] = 0, declared_page_count: Annotated[int | None, Ge(ge=0)] = None, declared_page_count_is_authoritative: Literal[False] = False, extension_mismatch: bool = False, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = ()) -> None
```

Safe bounded inspection of one verified non-macro DOCX.

### `DocxListInfo` (class)

```python
DocxListInfo(*, num_id: Annotated[str, MinLen(min_length=1)], abstract_num_id: str | None = None, level: Annotated[int, Ge(ge=0)], numbering_format: str | None = None, level_text: str | None = None, start_value: int | None = None, restart: bool | None = None, left_indent_twips: int | None = None, hanging_indent_twips: int | None = None) -> None
```

Structural Word numbering evidence without fabricated rendered prefixes.

### `DocxPackageInvalidError` (exception)


Raised when an OPC/ZIP or XML contract is malformed.

### `DocxPackageSummary` (class)

```python
DocxPackageSummary(*, member_count: Annotated[int, Ge(ge=1)], total_uncompressed_bytes: Annotated[int, Ge(ge=0)], xml_part_count: Annotated[int, Ge(ge=1)], relationship_count: Annotated[int, Ge(ge=0)], media_part_count: Annotated[int, Ge(ge=0)], embedded_part_count: Annotated[int, Ge(ge=0)], separator_footnote_count: Annotated[int, Ge(ge=0)] = 0, separator_endnote_count: Annotated[int, Ge(ge=0)] = 0, unsupported_feature_counts: tuple[tuple[str, int], ...] = ()) -> None
```

Bounded package facts and unsupported-feature counts.

### `DocxParagraph` (class)

```python
DocxParagraph(*, kind: Literal['paragraph'] = 'paragraph', paragraph_id: Annotated[str, MinLen(min_length=1)], text: str, runs: tuple[document_sdk.docx.models.DocxRun, ...] = (), style_id: str | None = None, style_name: str | None = None, outline_level: Annotated[int | None, Ge(ge=0), Le(le=9)] = None, is_heading: bool = False, alignment: str | None = None, language: str | None = None, list_info: document_sdk.docx.models.DocxListInfo | None = None, hyperlinks: tuple[document_sdk.docx.models.DocxHyperlink, ...] = (), bookmarks: tuple[document_sdk.docx.models.DocxBookmark, ...] = (), source: document_sdk.core.models.DocxSourceReference) -> None
```

One ordered paragraph with resolved structural formatting evidence.

### `DocxProcessingError` (exception)


Base failure for local DOCX inspection and analysis.

### `DocxProcessingLimits` (class)

```python
DocxProcessingLimits(*, max_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 512000000, max_package_members: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_total_uncompressed_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000000, max_member_uncompressed_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 256000000, max_compression_ratio: Annotated[float, Gt(gt=0), Le(le=10000)] = 200.0, max_xml_parts: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000, max_total_xml_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 256000000, max_xml_part_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 32000000, max_xml_elements: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000000, max_xml_depth: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 256, max_relationships: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000, max_text_characters: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000000, max_paragraphs: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000000, max_runs: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000000, max_tables: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000, max_table_rows: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000000, max_table_cells: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000000, max_nested_table_depth: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 32, max_sections: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000, max_headers: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_footers: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 10000, max_comments: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000, max_footnotes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000, max_endnotes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 1000000, max_hyperlinks: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000000, max_bookmarks: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000000, max_content_controls: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 2000000, max_media_parts: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000, max_embedded_parts: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 100000, max_embedded_total_bytes: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=10000000000)] = 512000000) -> None
```

Finite ZIP, XML, structure, text, and resource limits.

### `DocxResourceLimitError` (exception)

```python
DocxResourceLimitError(*, limit_name: str, observed: float, maximum: float) -> None
```

Raised before configured DOCX resource limits would be exceeded.

### `DocxRevisionView` (class)

```python
DocxRevisionView(*values)
```

Visible revision projection without accepting or rejecting revisions.

### `DocxRun` (class)

```python
DocxRun(*, run_id: Annotated[str, MinLen(min_length=1)], text: str, style: document_sdk.docx.models.DocxTextStyle = <factory>, hyperlink_id: str | None = None, footnote_id: str | None = None, endnote_id: str | None = None, comment_ids: tuple[str, ...] = (), resource_ids: tuple[str, ...] = (), revision_kind: str | None = None, source: document_sdk.core.models.DocxSourceReference) -> None
```

One ordered paragraph run and structural source.

### `DocxSection` (class)

```python
DocxSection(*, section_id: Annotated[str, MinLen(min_length=1)], section_index: Annotated[int, Ge(ge=0)], break_type: str | None = None, page_width_twips: Annotated[int | None, Gt(gt=0)] = None, page_height_twips: Annotated[int | None, Gt(gt=0)] = None, orientation: str | None = None, margin_top_twips: Annotated[int | None, Ge(ge=0)] = None, margin_right_twips: Annotated[int | None, Ge(ge=0)] = None, margin_bottom_twips: Annotated[int | None, Ge(ge=0)] = None, margin_left_twips: Annotated[int | None, Ge(ge=0)] = None, column_count: Annotated[int | None, Ge(ge=1)] = None, title_page: bool = False, even_and_odd_headers: bool = False, default_header_story_id: str | None = None, first_header_story_id: str | None = None, even_header_story_id: str | None = None, default_footer_story_id: str | None = None, first_footer_story_id: str | None = None, even_footer_story_id: str | None = None, source: document_sdk.core.models.DocxSourceReference) -> None
```

Section properties and deterministic header/footer story references.

### `DocxSourceChangedError` (exception)


Raised when authorized source bytes change during one operation.

### `DocxSourceReference` (class)

```python
DocxSourceReference(*, source_type: Literal['docx'] = 'docx', file_id: NonEmptyString, source_role: Literal['story', 'section', 'custom_property'] = 'story', package_part: NonEmptyString | None = None, story_type: NonEmptyString, story_id: NonEmptyString, block_index: Annotated[int, Ge(ge=0)], paragraph_index: Annotated[int | None, Ge(ge=0)] = None, run_index: Annotated[int | None, Ge(ge=0)] = None, table_index: Annotated[int | None, Ge(ge=0)] = None, table_path: tuple[typing.Annotated[int, FieldInfo(annotation=NoneType, required=True, metadata=[Ge(ge=0)])], ...] = (), row_index: Annotated[int | None, Ge(ge=0)] = None, cell_index: Annotated[int | None, Ge(ge=0)] = None, character_start: Annotated[int | None, Ge(ge=0)] = None, character_end: Annotated[int | None, Ge(ge=0)] = None, resource_id: NonEmptyString | None = None) -> None
```

A structural location in one DOCX story without fabricated pagination.

### `DocxStory` (class)

```python
DocxStory(*, story_id: Annotated[str, MinLen(min_length=1)], story_type: document_sdk.docx.models.DocxStoryType, part_role: Annotated[str, MinLen(min_length=1)], blocks: tuple[typing.Annotated[document_sdk.docx.models.DocxParagraph | document_sdk.docx.models.DocxTable, FieldInfo(annotation=NoneType, required=True, discriminator='kind')], ...] = (), sources: tuple[document_sdk.core.models.DocxSourceReference, ...] = ()) -> None
```

One ordered WordprocessingML story.

### `DocxStoryType` (class)

```python
DocxStoryType(*values)
```

WordprocessingML story categories represented without pagination.

### `DocxTable` (class)

```python
DocxTable(*, kind: Literal['table'] = 'table', table_id: Annotated[str, MinLen(min_length=1)], table_index: Annotated[int, Ge(ge=0)], rows: tuple[document_sdk.docx.models.DocxTableRow, ...] = (), logical_column_count: Annotated[int, Ge(ge=0)] = 0, caption: str | None = None, description: str | None = None, nested_depth: Annotated[int, Ge(ge=0)] = 0, source: document_sdk.core.models.DocxSourceReference) -> None
```

One ordered logical table, including nested tables.

### `DocxTableCell` (class)

```python
DocxTableCell(*, row_index: Annotated[int, Ge(ge=0)], column_index: Annotated[int, Ge(ge=0)], row_span: Annotated[int, Ge(ge=1)] = 1, column_span: Annotated[int, Ge(ge=1)] = 1, blocks: tuple[document_sdk.docx.models.DocxParagraph | document_sdk.docx.models.DocxTable, ...] = (), text: str = '', row_header: bool = False, source: document_sdk.core.models.DocxSourceReference) -> None
```

One non-overlapping logical table cell.

### `DocxTableRow` (class)

```python
DocxTableRow() -> None
```

One physical table row mapped to logical columns.

### `DocxTextStyle` (class)

```python
DocxTextStyle(*, bold: bool | None = None, italic: bool | None = None, underline: bool | None = None, strike: bool | None = None, double_strike: bool | None = None, subscript: bool | None = None, superscript: bool | None = None, small_caps: bool | None = None, all_caps: bool | None = None, hidden: bool | None = None, font_family: str | None = None, font_size_points: Annotated[float | None, Gt(gt=0)] = None, foreground_color: str | None = None, highlight: str | None = None, language: str | None = None) -> None
```

Common resolved run formatting without renderer claims.

### `DocxTrackChangesSummary` (class)

```python
DocxTrackChangesSummary(*, insertions: Annotated[int, Ge(ge=0)] = 0, deletions: Annotated[int, Ge(ge=0)] = 0, move_from: Annotated[int, Ge(ge=0)] = 0, move_to: Annotated[int, Ge(ge=0)] = 0, paragraph_property_changes: Annotated[int, Ge(ge=0)] = 0, run_property_changes: Annotated[int, Ge(ge=0)] = 0, section_property_changes: Annotated[int, Ge(ge=0)] = 0, table_property_changes: Annotated[int, Ge(ge=0)] = 0, authors: tuple[str, ...] = (), dates: tuple[datetime.datetime, ...] = (), sources: tuple[document_sdk.core.models.DocxSourceReference, ...] = ()) -> None
```

Complete safe revision counts and optional author/date evidence.

### `DocxUnsupportedPackageError` (exception)


Raised when an Office package is not a supported non-macro DOCX.

### `analyze_docx` (function)

```python
analyze_docx(path: pathlib.Path, *, options: document_sdk.docx.models.DocxAnalysisOptions | None = None, limits: document_sdk.docx.models.DocxProcessingLimits | None = None) -> document_sdk.docx.models.DocxAnalysisResult
```

Analyze one verified local DOCX.

### `inspect_docx` (function)

```python
inspect_docx(path: pathlib.Path, *, limits: document_sdk.docx.models.DocxProcessingLimits | None = None) -> document_sdk.docx.models.DocxInspection
```

Inspect one verified local DOCX.

## `document_sdk.excel`


### `AutoFilterColorPatch` (class)

```python
AutoFilterColorPatch(*, column_id: Annotated[int, Ge(ge=0), Lt(lt=16384)], differential_format_id: Annotated[int, Ge(ge=0), Le(le=100000)], cell_color: bool | None = None, hidden_button: bool = False, show_button: bool = True) -> None
```

One differential-format color filter column.

### `AutoFilterCustomCriterionPatch` (class)

```python
AutoFilterCustomCriterionPatch(*, operator: Literal['equal', 'notEqual', 'lessThan', 'lessThanOrEqual', 'greaterThan', 'greaterThanOrEqual'] = 'equal', value: Annotated[str, MinLen(min_length=1), MaxLen(max_length=32767)]) -> None
```

One explicit custom-filter comparison value.

### `AutoFilterCustomPatch` (class)

```python
AutoFilterCustomPatch(*, column_id: Annotated[int, Ge(ge=0), Lt(lt=16384)], criteria: Annotated[tuple[document_sdk.excel.models.AutoFilterCustomCriterionPatch, ...], MinLen(min_length=1), MaxLen(max_length=2)], and_operator: bool = False, hidden_button: bool = False, show_button: bool = True) -> None
```

One one- or two-condition custom filter column.

### `AutoFilterModification` (class)

```python
AutoFilterModification(*, sheet_name: WorksheetName, old_cell_range: str | None = None, new_cell_range: str | None = None, old_state_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], new_state_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet automatic-filter state replacement.

### `AutoFilterPatch` (class)

```python
AutoFilterPatch(*, sheet_name: WorksheetName, cell_range: NonEmptyString | None = None, value_filters: Annotated[tuple[document_sdk.excel.models.AutoFilterValueListPatch, ...], MaxLen(max_length=16384)] = (), custom_filters: Annotated[tuple[document_sdk.excel.models.AutoFilterCustomPatch, ...], MaxLen(max_length=16384)] = (), color_filters: Annotated[tuple[document_sdk.excel.models.AutoFilterColorPatch, ...], MaxLen(max_length=16384)] = (), sort_range: str | None = None, sort_conditions: Annotated[tuple[document_sdk.excel.models.AutoFilterSortConditionPatch, ...], MaxLen(max_length=16384)] = (), revision_uid: Annotated[str | None, _PydanticGeneralMetadata(pattern='^\\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\\}$')] = None, extension_list: Literal['absent', 'empty'] = 'absent') -> None
```

Set, replace, or clear one worksheet's standard automatic filter.

### `AutoFilterSortConditionPatch` (class)

```python
AutoFilterSortConditionPatch(*, cell_range: NonEmptyString, descending: bool = False) -> None
```

One ordinary value-sort condition inside an automatic-filter range.

### `AutoFilterValueListPatch` (class)

```python
AutoFilterValueListPatch(*, column_id: Annotated[int, Ge(ge=0), Lt(lt=16384)], values: Annotated[tuple[NonEmptyString, ...], MaxLen(max_length=10000)] = (), include_blank: bool = False, hidden_button: bool = False, show_button: bool = True) -> None
```

One value-list filter for a zero-based column inside a filter range.

### `CellAlignmentPatch` (class)

```python
CellAlignmentPatch(*, horizontal: Optional[Literal['general', 'left', 'center', 'right', 'fill', 'justify', 'centerContinuous', 'distributed']] = None, vertical: Optional[Literal['top', 'center', 'bottom', 'justify', 'distributed']] = None, text_rotation: int | None = None, wrap_text: bool | None = None, shrink_to_fit: bool | None = None, indent: Annotated[int | None, Ge(ge=0), Le(le=250)] = None, relative_indent: Annotated[int | None, Ge(ge=-15), Le(le=15)] = None, justify_last_line: bool | None = None, reading_order: Annotated[int | None, Ge(ge=0), Le(le=2)] = None) -> None
```

A complete alignment component for one cell format.

### `CellBorderPatch` (class)

```python
CellBorderPatch(*, left: document_sdk.excel.models.CellBorderSidePatch | None = None, right: document_sdk.excel.models.CellBorderSidePatch | None = None, top: document_sdk.excel.models.CellBorderSidePatch | None = None, bottom: document_sdk.excel.models.CellBorderSidePatch | None = None, diagonal: document_sdk.excel.models.CellBorderSidePatch | None = None, vertical: document_sdk.excel.models.CellBorderSidePatch | None = None, horizontal: document_sdk.excel.models.CellBorderSidePatch | None = None, start: document_sdk.excel.models.CellBorderSidePatch | None = None, end: document_sdk.excel.models.CellBorderSidePatch | None = None, diagonal_up: bool | None = None, diagonal_down: bool | None = None, outline: bool | None = None) -> None
```

A complete border component for one cell format.

### `CellBorderSidePatch` (class)

```python
CellBorderSidePatch(*, style: Optional[Literal['dashDot', 'dashDotDot', 'dashed', 'dotted', 'double', 'hair', 'medium', 'mediumDashDot', 'mediumDashDotDot', 'mediumDashed', 'slantDashDot', 'thick', 'thin']] = None, color: document_sdk.excel.models.CellStyleColor | None = None) -> None
```

One complete side of a cell border.

### `CellDiff` (class)

```python
CellDiff(*, difference_type: Literal['value', 'formula', 'cached_value', 'data_type', 'style', 'hyperlink', 'comment'], sheet_name: NonEmptyString, coordinate: NonEmptyString, old_value: ExcelPatchScalar = None, new_value: ExcelPatchScalar = None, old_source: document_sdk.core.models.ExcelSourceReference | None = None, new_source: document_sdk.core.models.ExcelSourceReference | None = None) -> None
```

One cell-level workbook difference.

### `CellFontPatch` (class)

```python
CellFontPatch(*, name: str | None = None, size: Annotated[float | None, Gt(gt=0), Le(le=409.0)] = None, bold: bool | None = None, italic: bool | None = None, underline: Optional[Literal['single', 'double', 'singleAccounting', 'doubleAccounting']] = None, strike: bool | None = None, color: document_sdk.excel.models.CellStyleColor | None = None, vert_align: Optional[Literal['baseline', 'superscript', 'subscript']] = None, charset: Annotated[int | None, Ge(ge=0), Le(le=255)] = None, family: Annotated[float | None, Ge(ge=0), Le(le=14)] = None, scheme: Optional[Literal['major', 'minor']] = None, outline: bool | None = None, shadow: bool | None = None, condense: bool | None = None, extend: bool | None = None) -> None
```

A complete font component for one cell format.

### `CellFormatModification` (class)

```python
CellFormatModification(*, sheet_name: WorksheetName, coordinate: NonEmptyString, changed_components: Annotated[tuple[Literal['font', 'fill', 'border', 'alignment', 'number_format', 'named_style', 'quote_prefix', 'pivot_button'], ...], MinLen(min_length=1)], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified workbook cell-format modification.

### `CellFormatPatch` (class)

```python
CellFormatPatch(*, sheet_name: WorksheetName, coordinate: NonEmptyString, font: document_sdk.excel.models.CellFontPatch | None = None, fill: document_sdk.excel.models.CellPatternFillPatch | None = None, border: document_sdk.excel.models.CellBorderPatch | None = None, alignment: document_sdk.excel.models.CellAlignmentPatch | None = None, number_format: ExcelNumberFormatCode | None = None, named_style: NonEmptyString | None = None, quote_prefix: bool | None = None, pivot_button: bool | None = None) -> None
```

One addressed cell-format patch with explicit complete components.

### `CellGradientFillPatch` (class)

```python
CellGradientFillPatch(*, fill_type: Literal['linear', 'path'] = 'linear', degree: float = 0.0, left: Annotated[float, Ge(ge=0), Le(le=1)] = 0.0, right: Annotated[float, Ge(ge=0), Le(le=1)] = 0.0, top: Annotated[float, Ge(ge=0), Le(le=1)] = 0.0, bottom: Annotated[float, Ge(ge=0), Le(le=1)] = 0.0, stops: Annotated[tuple[document_sdk.excel.models.CellGradientStopPatch, ...], MinLen(min_length=2), MaxLen(max_length=64)]) -> None
```

A complete linear or path gradient-fill component.

### `CellGradientStopPatch` (class)

```python
CellGradientStopPatch(*, position: Annotated[float, Ge(ge=0), Le(le=1)], color: document_sdk.excel.models.CellStyleColor) -> None
```

One ordered color stop in a complete gradient fill.

### `CellModification` (class)

```python
CellModification(*, sheet_name: WorksheetName, coordinate: NonEmptyString, old_value: ExcelPatchScalar = None, new_value: ExcelPatchScalar = None, old_formula: str | None = None, new_formula: str | None = None, number_format: str | None = None, source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified workbook cell modification.

### `CellPatch` (class)

```python
CellPatch(*, sheet_name: WorksheetName, coordinate: NonEmptyString, content: document_sdk.excel.models.CellPatchValue) -> None
```

One addressed worksheet patch.

### `CellPatchValue` (class)

```python
CellPatchValue(*, kind: Literal['value', 'error', 'formula', 'array_formula', 'clear'], value: ExcelPatchScalar = None, number_format: ExcelNumberFormatCode | None = None, formula_range: str | None = None, clear_existing_cells: tuple[NonEmptyString, ...] = ()) -> None
```

Explicit value, formula, or clear operation for a cell.

### `CellPatternFillPatch` (class)

```python
CellPatternFillPatch(*, pattern_type: Optional[Literal['none', 'solid', 'darkDown', 'darkGray', 'darkGrid', 'darkHorizontal', 'darkTrellis', 'darkUp', 'darkVertical', 'gray0625', 'gray125', 'lightDown', 'lightGray', 'lightGrid', 'lightHorizontal', 'lightTrellis', 'lightUp', 'lightVertical', 'mediumGray']] = None, foreground_color: document_sdk.excel.models.CellStyleColor | None = None, background_color: document_sdk.excel.models.CellStyleColor | None = None) -> None
```

A complete pattern-fill component for one cell format.

### `CellStyleColor` (class)

```python
CellStyleColor(*, rgb: str | None = None, indexed: Annotated[int | None, Ge(ge=0), Le(le=65)] = None, theme: Annotated[int | None, Ge(ge=0)] = None, auto: bool | None = None, tint: Annotated[float, Ge(ge=-1.0), Le(le=1.0)] = 0.0) -> None
```

One explicit OOXML-compatible cell-style color.

### `CellWriteRequest` (class)

```python
CellWriteRequest(*, coordinate: NonEmptyString, value: ExcelValue) -> None
```

A value to write to one Excel coordinate.

### `ChartsheetFeatureInventory` (class)

```python
ChartsheetFeatureInventory(*, name: WorksheetName, workbook_order: Annotated[int, Ge(ge=1)], visibility: SheetVisibility, part_present: bool, drawing_relationship_count: Annotated[int, Ge(ge=0)], drawing_part_count: Annotated[int, Ge(ge=0)], chart_part_count: Annotated[int, Ge(ge=0)], printer_settings_present: bool, page_margins_present: bool, page_setup_present: bool, header_footer_present: bool, sheet_protection_present: bool, external_relationship_count: Annotated[int, Ge(ge=0)]) -> None
```

Serializable structural inventory for one non-cell-bearing Chartsheet.

### `ColumnDimensionModification` (class)

```python
ColumnDimensionModification(*, sheet_name: WorksheetName, start_column: str, end_column: str, old_width: Annotated[float | None, Gt(gt=0)] = None, new_width: Annotated[float | None, Gt(gt=0)] = None, old_hidden: bool, new_hidden: bool, old_best_fit: bool = False, new_best_fit: bool = False, old_style_fingerprint: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, new_style_fingerprint: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, style_changed_components: Annotated[tuple[Literal['font', 'fill', 'border', 'alignment', 'number_format', 'named_style', 'quote_prefix', 'pivot_button'], ...], MaxLen(max_length=8)] = (), source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet column-dimension modification.

### `ColumnDimensionPatch` (class)

```python
ColumnDimensionPatch(*, sheet_name: WorksheetName, start_column: str, end_column: str | None = None, width: Annotated[float | None, Gt(gt=0), Le(le=255.0)] = None, clear_width: bool = False, hidden: bool | None = None, best_fit: bool | None = None, font: document_sdk.excel.models.CellFontPatch | None = None, fill: document_sdk.excel.models.CellPatternFillPatch | None = None, border: document_sdk.excel.models.CellBorderPatch | None = None, alignment: document_sdk.excel.models.CellAlignmentPatch | None = None, number_format: ExcelNumberFormatCode | None = None, named_style: NonEmptyString | None = None, quote_prefix: bool | None = None, pivot_button: bool | None = None) -> None
```

One bounded worksheet column-dimension patch.

### `ColumnSchema` (class)

```python
ColumnSchema(*, name: NonEmptyString, data_type: Literal['string', 'integer', 'decimal', 'percentage', 'date', 'datetime', 'boolean'] = 'string', required: bool = True, nullable: bool = True, unique: bool = False, minimum: decimal.Decimal | datetime.date | datetime.datetime | None = None, maximum: decimal.Decimal | datetime.date | datetime.datetime | None = None, minimum_length: Annotated[int | None, Ge(ge=0)] = None, maximum_length: Annotated[int | None, Ge(ge=0)] = None, pattern: str | None = None, allowed_values: tuple[ExcelPatchScalar, ...] = ()) -> None
```

Generic validation rules for one table column.

### `ColumnWidthFeature` (class)

```python
ColumnWidthFeature(*, column: NonEmptyString, width: Annotated[float, Gt(gt=0)]) -> None
```

One explicitly configured worksheet column width.

### `ConditionalFormattingBlockPatch` (class)

```python
ConditionalFormattingBlockPatch(*, cell_ranges: Annotated[tuple[NonEmptyString, ...], MinLen(min_length=1), MaxLen(max_length=1000)], rules: Annotated[tuple[document_sdk.excel.models.ConditionalFormattingRulePatch, ...], MinLen(min_length=1), MaxLen(max_length=10000)]) -> None
```

One target range set and its ordered conditional-formatting rules.

### `ConditionalFormattingModification` (class)

```python
ConditionalFormattingModification(*, sheet_name: WorksheetName, old_rule_count: Annotated[int, Ge(ge=0)], new_rule_count: Annotated[int, Ge(ge=0)], old_rule_set_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], new_rule_set_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet conditional-formatting replacement.

### `ConditionalFormattingRulePatch` (class)

```python
ConditionalFormattingRulePatch(*, rule_type: Literal['expression', 'cellIs', 'containsText', 'notContainsText', 'beginsWith', 'endsWith', 'containsBlanks', 'notContainsBlanks', 'duplicateValues', 'top10'], operator: Optional[Literal['lessThan', 'lessThanOrEqual', 'equal', 'notEqual', 'greaterThanOrEqual', 'greaterThan', 'between', 'notBetween', 'containsText', 'notContains', 'beginsWith', 'endsWith']] = None, formulas: Annotated[tuple[str, ...], MaxLen(max_length=2)] = (), text: str | None = None, stop_if_true: bool = False, rank: Annotated[int | None, Ge(ge=1)] = None, bottom: bool | None = None, differential_format: document_sdk.excel.models.DifferentialFormatPatch | None = None) -> None
```

One standard conditional-formatting rule in priority order.

### `DataValidationModification` (class)

```python
DataValidationModification(*, sheet_name: WorksheetName, old_rule_count: Annotated[int, Ge(ge=0)], new_rule_count: Annotated[int, Ge(ge=0)], old_rule_set_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], new_rule_set_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet data-validation rule-set replacement.

### `DataValidationRulePatch` (class)

```python
DataValidationRulePatch(*, representation: Literal['standard', 'x14'] = 'standard', cell_ranges: Annotated[tuple[NonEmptyString, ...], MinLen(min_length=1), MaxLen(max_length=1000)], validation_type: Optional[Literal['list', 'whole', 'decimal', 'date', 'time', 'textLength', 'custom']] = None, operator: Optional[Literal['between', 'notBetween', 'equal', 'notEqual', 'lessThan', 'lessThanOrEqual', 'greaterThan', 'greaterThanOrEqual']] = None, formula1: str | None = None, formula2: str | None = None, allow_blank: bool = False, show_error_message: bool = False, show_input_message: bool = False, show_drop_down: bool = False, error_style: Optional[Literal['stop', 'warning', 'information']] = None, error: Annotated[str | None, MaxLen(max_length=255)] = None, error_title: Annotated[str | None, MaxLen(max_length=32)] = None, prompt: Annotated[str | None, MaxLen(max_length=255)] = None, prompt_title: Annotated[str | None, MaxLen(max_length=32)] = None, revision_uid: Annotated[str | None, _PydanticGeneralMetadata(pattern='^\\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\\}$')] = None, clear_revision_uid: bool = False) -> None
```

One complete standard worksheet data-validation rule.

### `DefinedNameFeature` (class)

```python
DefinedNameFeature(*, name: NonEmptyString, scope: WorksheetName | None = None, kind: Literal['range', 'constant', 'formula', 'external', 'reserved'], definition: str | None = None, destinations: tuple[document_sdk.core.models.ExcelSourceReference, ...] = (), external_reference: bool = False, fillable: bool = False) -> None
```

One workbook-defined name without external target details.

### `DefinedNameModification` (class)

```python
DefinedNameModification(*, name: NonEmptyString, operation: Literal['create', 'update', 'delete'], scope_sheet_name: WorksheetName | None = None, old_formula: str | None = None, new_formula: str | None = None, old_hidden: bool | None = None, new_hidden: bool | None = None, source_file_id: NonEmptyString, output_file_id: NonEmptyString) -> None
```

One verified local-workbook defined-name change.

### `DefinedNamePatch` (class)

```python
DefinedNamePatch(*, name: NonEmptyString, operation: Literal['create', 'update', 'delete'], formula: str | None = None, scope_sheet_name: WorksheetName | None = None, hidden: bool = False, allow_external_reference: bool = False) -> None
```

Create, update, or delete one local-workbook defined name.

### `DifferentialFormatPatch` (class)

```python
DifferentialFormatPatch(*, font: document_sdk.excel.models.CellFontPatch | None = None, fill: document_sdk.excel.models.CellPatternFillPatch | document_sdk.excel.models.CellGradientFillPatch | None = None, border: document_sdk.excel.models.CellBorderPatch | None = None, alignment: document_sdk.excel.models.CellAlignmentPatch | None = None, number_format: ExcelNumberFormatCode | None = None) -> None
```

A complete supported differential style for conditional formatting.

### `DrawingMarkerPatch` (class)

```python
DrawingMarkerPatch(*, column: Annotated[int, Ge(ge=0), Lt(lt=16384)], column_offset: Annotated[int, Ge(ge=0), Le(le=2147483647)] = 0, row: Annotated[int, Ge(ge=0), Lt(lt=1048576)], row_offset: Annotated[int, Ge(ge=0), Le(le=2147483647)] = 0) -> None
```

One zero-based DrawingML worksheet anchor marker.

### `ExcelAdditionalSourceDetail` (class)

```python
ExcelAdditionalSourceDetail(*, category: Literal['custom_xml', 'extension', 'other', 'source_structure'], sheet_names: tuple[WorksheetName, ...] = (), part_name: NonEmptyString, path: NonEmptyString, parent_path: str | None = None, document_order_key: tuple[int, ...], node_type: Literal['element', 'text', 'tail', 'comment', 'processing_instruction', 'namespace_declaration'], namespace: str | None = None, name: NonEmptyString, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), text: str | None = None, declared_prefix: str | None = None, child_count: Annotated[int, Ge(ge=0)]) -> None
```

One ordered XML source occurrence outside a typed business projection.

### `ExcelAutoFilterDetail` (class)

```python
ExcelAutoFilterDetail(*, sheet_names: tuple[WorksheetName, ...], part_name: NonEmptyString, path: NonEmptyString, cell_range: str | None = None, source_kind: Literal['worksheet', 'table'], attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

One worksheet or table auto-filter including filters and sort state.

### `ExcelChartDetail` (class)

```python
ExcelChartDetail(*, sheet_names: tuple[WorksheetName, ...], source_relationships: tuple[document_sdk.excel.semantic_details.ExcelSourceRelationshipReference, ...] = (), part_name: NonEmptyString, chart_types: tuple[NonEmptyString, ...], title_text: tuple[str, ...] = (), series: tuple[document_sdk.excel.semantic_details.ExcelChartSeriesDetail, ...] = (), axis_ids: tuple[str, ...] = (), attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

Selected deterministic chart facts for one chart package part.

### `ExcelChartSeriesDetail` (class)

```python
ExcelChartSeriesDetail(*, index: Annotated[int | None, Ge(ge=0)] = None, order: Annotated[int | None, Ge(ge=0)] = None, title_formula: str | None = None, title_text: str | None = None, category_formula: str | None = None, value_formula: str | None = None, bubble_size_formula: str | None = None, literal_values: tuple[str, ...] = ()) -> None
```

One chart series with source formula references and literal values.

### `ExcelColumnDetail` (class)

```python
ExcelColumnDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, min_column: Annotated[int, Ge(ge=1), Le(le=16384)], max_column: Annotated[int, Ge(ge=1), Le(le=16384)], width: Annotated[float | None, Ge(ge=0)] = None, effective_width: Annotated[float | None, Ge(ge=0)] = None, hidden: bool, outline_level: Annotated[int, Ge(ge=0)], collapsed: bool, style_id: Annotated[int | None, Ge(ge=0)] = None, best_fit: bool, custom_width: bool, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One physical column span with raw and default-resolved properties.

### `ExcelCommentDetail` (class)

```python
ExcelCommentDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, coordinate: NonEmptyString, author_id: Annotated[int, Ge(ge=0)], author: str, text: str, rich_text_runs: tuple[str, ...] = (), attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One legacy comment with its author, text, and exact cell location.

### `ExcelComparisonLimitError` (exception)

```python
ExcelComparisonLimitError(*, observed_cells: int, max_cells: int) -> None
```

Raised when comparison input exceeds its configured cell bound.

### `ExcelConditionalFormattingDetail` (class)

```python
ExcelConditionalFormattingDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, cell_ranges: tuple[NonEmptyString, ...], pivot: bool, rules: tuple[document_sdk.excel.semantic_details.ExcelConditionalFormattingRuleDetail, ...], attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One conditional-formatting block and every declared rule.

### `ExcelConditionalFormattingRuleDetail` (class)

```python
ExcelConditionalFormattingRuleDetail(*, rule_type: str | None = None, priority: Annotated[int | None, Ge(ge=0)] = None, differential_style_id: Annotated[int | None, Ge(ge=0)] = None, stop_if_true: bool, operator: str | None = None, text: str | None = None, time_period: str | None = None, rank: Annotated[int | None, Ge(ge=0)] = None, percent: bool, bottom: bool, above_average: bool | None = None, equal_average: bool, standard_deviations: int | None = None, formulas: tuple[str, ...] = (), attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

One conditional-formatting rule with its ordered structured payload.

### `ExcelDataValidationDetail` (class)

```python
ExcelDataValidationDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, namespace: str | None = None, cell_ranges: tuple[NonEmptyString, ...], validation_type: str | None = None, operator: str | None = None, error_style: str | None = None, ime_mode: str | None = None, allow_blank: bool, show_drop_down: bool, show_input_message: bool, show_error_message: bool, error_title: str | None = None, error: str | None = None, prompt_title: str | None = None, prompt: str | None = None, formulas: tuple[str, ...] = (), attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

One complete worksheet data-validation rule and its target ranges.

### `ExcelDefinedNameDetail` (class)

```python
ExcelDefinedNameDetail(*, part_name: NonEmptyString, path: NonEmptyString, name: NonEmptyString, definition: str, local_sheet_id: Annotated[int | None, Ge(ge=0)] = None, scope_sheet_name: WorksheetName | None = None, hidden: bool, function: bool, vb_procedure: bool, xlm: bool, function_group_id: Annotated[int | None, Ge(ge=0)] = None, shortcut_key: str | None = None, publish_to_server: bool, workbook_parameter: bool, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One complete workbook defined-name declaration.

### `ExcelDrawingDetail` (class)

```python
ExcelDrawingDetail(*, sheet_names: tuple[WorksheetName, ...], source_relationships: tuple[document_sdk.excel.semantic_details.ExcelSourceRelationshipReference, ...] = (), part_name: NonEmptyString, path: NonEmptyString, anchor_type: Literal['one_cell', 'two_cell', 'absolute'], from_marker: document_sdk.excel.semantic_details.ExcelDrawingMarkerDetail | None = None, to_marker: document_sdk.excel.semantic_details.ExcelDrawingMarkerDetail | None = None, position_x: Annotated[int | None, Ge(ge=0)] = None, position_y: Annotated[int | None, Ge(ge=0)] = None, extent_cx: Annotated[int | None, Ge(ge=0)] = None, extent_cy: Annotated[int | None, Ge(ge=0)] = None, object_type: NonEmptyString, object_name: str | None = None, object_description: str | None = None, relationship_id: str | None = None, target_part: str | None = None, external_target_sha256: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, target_content_type: str | None = None, target_sha256: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

One worksheet or Chartsheet drawing anchor and its related object.

### `ExcelDrawingMarkerDetail` (class)

```python
ExcelDrawingMarkerDetail(*, column: Annotated[int, Ge(ge=0)], column_offset: Annotated[int, Ge(ge=0)], row: Annotated[int, Ge(ge=0)], row_offset: Annotated[int, Ge(ge=0)]) -> None
```

One DrawingML anchor marker in zero-based sheet coordinates.

### `ExcelHyperlinkDetail` (class)

```python
ExcelHyperlinkDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, cell_range: NonEmptyString, relationship_id: str | None = None, target_part: str | None = None, external_target_sha256: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, location: str | None = None, display: str | None = None, tooltip: str | None = None, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One worksheet hyperlink with an internal location or redacted target.

### `ExcelModificationError` (exception)


Raised when a requested workbook modification is invalid or unsafe.

### `ExcelPackageLimitError` (exception)

```python
ExcelPackageLimitError(*, limit_name: str, observed: int, maximum: int) -> None
```

Raised before unsafe OOXML package expansion.

### `ExcelPackageLimits` (class)

```python
ExcelPackageLimits(*, package_members: Annotated[int, Gt(gt=0)] = 10000, total_uncompressed_bytes: Annotated[int, Gt(gt=0)] = 536870912, xml_member_bytes: Annotated[int, Gt(gt=0)] = 67108864, compression_ratio: Annotated[int, Gt(gt=0)] = 1000, worksheet_feature_records: Annotated[int, Gt(gt=0)] = 100000, shared_string_entries: Annotated[int, Gt(gt=0)] = 1000000, semantic_detail_records: Annotated[int, Gt(gt=0)] = 1000000, semantic_detail_text_characters: Annotated[int, Gt(gt=0)] = 67108864, semantic_detail_xml_depth: Annotated[int, Gt(gt=0)] = 256) -> None
```

Explicit finite OOXML expansion limits for trusted large workbooks.

### `ExcelPackagePartDetail` (class)

```python
ExcelPackagePartDetail(*, part_name: NonEmptyString, content_type: str | None = None, kind: PackagePartKind, semantic_representation: Literal['typed', 'structured', 'identity_only'] = 'identity_only', size_bytes: Annotated[int, Ge(ge=0)], sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')]) -> None
```

Identity and content classification for one validated package member.

### `ExcelPagePrintDetail` (class)

```python
ExcelPagePrintDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, kind: NonEmptyString, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), text: str | None = None) -> None
```

One worksheet page, print, header/footer, or break declaration.

### `ExcelPatchScalar` (value)


Type alias.

### `ExcelPhysicalCellDetail` (class)

```python
ExcelPhysicalCellDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, coordinate: NonEmptyString, namespace: str | None = None, raw_type: str | None = None, direct_style_id: Annotated[int | None, Ge(ge=0)] = None, effective_style_id: Annotated[int, Ge(ge=0)], style_source: Literal['cell', 'row', 'column', 'default'], formula_present: bool, formula_kind: Optional[Literal['ordinary', 'shared', 'array', 'dynamic_array']] = None, formula_text: str | None = None, formula_shared_index: Annotated[int | None, Ge(ge=0)] = None, formula_range: str | None = None, formula_attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), cached_value_present: bool, raw_cached_value: str | None = None, inline_string_present: bool, inline_text: str | None = None, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One physical ``c`` element, including represented empty forms.

### `ExcelRelationshipDetail` (class)

```python
ExcelRelationshipDetail(*, source_part: str, relationship_part: NonEmptyString, path: NonEmptyString, relationship_id: NonEmptyString, relationship_type: NonEmptyString, target_part: str | None = None, raw_internal_target: str | None = None, target_mode: Optional[Literal['Internal', 'External']] = None, external: bool, external_target_sha256: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')] = None, additional_attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One OOXML relationship without exposing external target text.

### `ExcelRowDetail` (class)

```python
ExcelRowDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, row: Annotated[int, Ge(ge=1), Le(le=1048576)], height: Annotated[float | None, Ge(ge=0)] = None, effective_height: Annotated[float | None, Ge(ge=0)] = None, hidden: bool, outline_level: Annotated[int, Ge(ge=0)], collapsed: bool, style_id: Annotated[int | None, Ge(ge=0)] = None, custom_height: bool, custom_format: bool, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One physical row with raw and default-resolved properties.

### `ExcelSourceAttribute` (class)

```python
ExcelSourceAttribute(*, namespace: str | None = None, name: NonEmptyString, value: str) -> None
```

One exact XML attribute represented by namespace, local name, and value.

### `ExcelSourceProperty` (class)

```python
ExcelSourceProperty(*, path: NonEmptyString, namespace: str | None = None, name: NonEmptyString, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), text: str | None = None) -> None
```

One ordered property inside a structured OOXML source record.

### `ExcelSourceRelationshipReference` (class)

```python
ExcelSourceRelationshipReference(*, source_part: NonEmptyString, relationship_id: NonEmptyString) -> None
```

One exact relationship reference that attaches a semantic object.

### `ExcelStyleDetail` (class)

```python
ExcelStyleDetail(*, component: StyleComponent, index: Annotated[int, Ge(ge=0)], part_name: NonEmptyString, path: NonEmptyString, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

One indexed style catalog component with its complete structured subtree.

### `ExcelTableColumnDetail` (class)

```python
ExcelTableColumnDetail(*, column_id: Annotated[int, Gt(gt=0)], name: str, unique_name: str | None = None, totals_row_label: str | None = None, totals_row_function: str | None = None, calculated_column_formula: str | None = None, totals_row_formula: str | None = None, data_cell_style: str | None = None, header_row_cell_style: str | None = None, totals_row_cell_style: str | None = None, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One declared table column and its formula or totals behavior.

### `ExcelTableDetail` (class)

```python
ExcelTableDetail(*, sheet_names: tuple[WorksheetName, ...], source_relationships: tuple[document_sdk.excel.semantic_details.ExcelSourceRelationshipReference, ...] = (), part_name: NonEmptyString, path: NonEmptyString, table_id: Annotated[int, Gt(gt=0)], name: NonEmptyString, display_name: NonEmptyString, cell_range: NonEmptyString, header_row_count: Annotated[int, Ge(ge=0)], totals_row_count: Annotated[int, Ge(ge=0)], totals_row_shown: bool, columns: tuple[document_sdk.excel.semantic_details.ExcelTableColumnDetail, ...] = (), style_name: str | None = None, show_first_column: bool, show_last_column: bool, show_row_stripes: bool, show_column_stripes: bool, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), properties: tuple[document_sdk.excel.semantic_details.ExcelSourceProperty, ...] = ()) -> None
```

One relationship-bound worksheet table with columns and style facts.

### `ExcelTableFeature` (class)

```python
ExcelTableFeature(*, name: NonEmptyString, display_name: NonEmptyString, cell_range: NonEmptyString, source: document_sdk.core.models.ExcelSourceReference) -> None
```

Safe inventory data for one standard Excel table.

### `ExcelViewDetail` (class)

```python
ExcelViewDetail(*, sheet_name: WorksheetName | None = None, part_name: NonEmptyString, path: NonEmptyString, kind: NonEmptyString, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = ()) -> None
```

One workbook/worksheet view, pane, or selection declaration.

### `ExcelWorkbookPropertyDetail` (class)

```python
ExcelWorkbookPropertyDetail(*, part_name: NonEmptyString, path: NonEmptyString, kind: NonEmptyString, namespace: str | None = None, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), text: str | None = None) -> None
```

One workbook property or calculation declaration.

### `ExcelWorksheetPropertyDetail` (class)

```python
ExcelWorksheetPropertyDetail(*, sheet_name: WorksheetName, part_name: NonEmptyString, path: NonEmptyString, kind: NonEmptyString, namespace: str | None = None, attributes: tuple[document_sdk.excel.semantic_details.ExcelSourceAttribute, ...] = (), text: str | None = None) -> None
```

One worksheet or Chartsheet property or structural declaration.

### `ExistingCellFormatRangeModification` (class)

```python
ExistingCellFormatRangeModification(*, sheet_name: WorksheetName, cell_ranges: Annotated[tuple[NonEmptyString, ...], MinLen(min_length=1), MaxLen(max_length=100000)], target_cell_count: Annotated[int, Gt(gt=0)], changed_components: Annotated[tuple[Literal['font', 'fill', 'border', 'alignment', 'number_format', 'named_style', 'quote_prefix', 'pivot_button'], ...], MinLen(min_length=1)], source_file_id: NonEmptyString, output_file_id: NonEmptyString) -> None
```

Compact evidence for one verified existing-cell range-format operation.

### `ExistingCellFormatRangePatch` (class)

```python
ExistingCellFormatRangePatch(*, sheet_name: WorksheetName, cell_ranges: Annotated[tuple[NonEmptyString, ...], MinLen(min_length=1), MaxLen(max_length=100000)], font: document_sdk.excel.models.CellFontPatch | None = None, fill: document_sdk.excel.models.CellPatternFillPatch | None = None, border: document_sdk.excel.models.CellBorderPatch | None = None, alignment: document_sdk.excel.models.CellAlignmentPatch | None = None, number_format: ExcelNumberFormatCode | None = None, named_style: NonEmptyString | None = None, quote_prefix: bool | None = None, pivot_button: bool | None = None) -> None
```

Apply complete format components only to existing cells in bounded ranges.

### `ExternalLinkRemovalPatch` (class)

```python
ExternalLinkRemovalPatch(*, link_index: Annotated[int, Ge(ge=1), Le(le=10000)]) -> None
```

Remove one one-based external-link identity and compact later indexes.

### `FeatureDiff` (class)

```python
FeatureDiff(*, difference_type: NonEmptyString, feature: NonEmptyString, old_state: FeatureState = None, new_state: FeatureState = None, old_source: document_sdk.core.models.ExcelSourceReference | None = None, new_source: document_sdk.core.models.ExcelSourceReference | None = None) -> None
```

One structural workbook or worksheet difference.

### `FormulaKind` (value)


Type alias.

### `FormulaView` (value)


Type alias.

### `FreezePaneModification` (class)

```python
FreezePaneModification(*, sheet_name: WorksheetName, old_coordinate: str | None = None, new_coordinate: str | None = None, source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet frozen-pane change.

### `FreezePanePatch` (class)

```python
FreezePanePatch(*, sheet_name: WorksheetName, coordinate: NonEmptyString | None = None) -> None
```

Set or clear the frozen-pane anchor for one worksheet.

### `HyperlinkModification` (class)

```python
HyperlinkModification(*, sheet_name: WorksheetName, old_count: Annotated[int, Ge(ge=0)], new_count: Annotated[int, Ge(ge=0)], old_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], new_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet hyperlink-set replacement.

### `HyperlinkRecordPatch` (class)

```python
HyperlinkRecordPatch(*, cell_range: NonEmptyString, target: Annotated[str | None, MaxLen(max_length=8192)] = None, location: Annotated[str | None, MaxLen(max_length=8192)] = None, display: Annotated[str | None, MaxLen(max_length=32767)] = None, tooltip: Annotated[str | None, MaxLen(max_length=32767)] = None) -> None
```

One complete internal or safely-schemed external worksheet hyperlink.

### `LegacyCommentRecordPatch` (class)

```python
LegacyCommentRecordPatch(*, coordinate: NonEmptyString, author: NonEmptyString, text: Annotated[str, MaxLen(max_length=32767)]) -> None
```

One complete legacy worksheet comment record.

### `LegacyCommentsModification` (class)

```python
LegacyCommentsModification(*, sheet_name: WorksheetName, old_count: Annotated[int, Ge(ge=0)], new_count: Annotated[int, Ge(ge=0)], old_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], new_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet legacy-comment-set replacement.

### `LocatedWorkbookFeature` (class)

```python
LocatedWorkbookFeature(*, feature_type: NonEmptyString, source: document_sdk.core.models.ExcelSourceReference, details: str | None = None) -> None
```

A workbook feature with a meaningful worksheet or cell location.

### `MacroSheetFeatureInventory` (class)

```python
MacroSheetFeatureInventory(*, name: WorksheetName, workbook_order: Annotated[int, Ge(ge=1)], visibility: SheetVisibility, part_present: bool, dimension_reference: str | None = None, row_count: Annotated[int, Ge(ge=0)], cell_count: Annotated[int, Ge(ge=0)], formula_count: Annotated[int, Ge(ge=0)], value_count: Annotated[int, Ge(ge=0)], part_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], formula_digest_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], shared_string_reference_count: Annotated[int, Ge(ge=0)], shared_string_digest_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], non_formula_cell_digest_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], relationship_count: Annotated[int, Ge(ge=0)], printer_settings_present: bool, external_relationship_count: Annotated[int, Ge(ge=0)], defined_name_reference_count: Annotated[int, Ge(ge=0)], defined_name_digest_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')]) -> None
```

Safe structural inventory for one non-executed Excel 4.0 Macro Sheet.

### `MergedRangeModification` (class)

```python
MergedRangeModification(*, sheet_name: WorksheetName, cell_range: NonEmptyString, operation: Literal['merge', 'unmerge'], source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet merge or unmerge operation.

### `MergedRangePatch` (class)

```python
MergedRangePatch(*, sheet_name: WorksheetName, cell_range: NonEmptyString, operation: Literal['merge', 'unmerge']) -> None
```

Merge or unmerge one bounded worksheet range.

### `NamedRangePatch` (class)

```python
NamedRangePatch(*, name: NonEmptyString, values: Annotated[tuple[tuple[document_sdk.excel.models.CellPatchValue, ...], ...], MinLen(min_length=1)]) -> None
```

A rectangular value matrix for one workbook-defined name.

### `NormalizationOptions` (class)

```python
NormalizationOptions(*, trim_whitespace: bool = True, unicode_form: Literal['none', 'NFC', 'NFKC'] = 'NFC', normalize_width: bool = False, case: Literal['preserve', 'lower', 'upper', 'casefold'] = 'preserve', blank_values: tuple[str, ...] = ('',), thousands_separator: str = ',', decimal_separator: str = '.', true_values: tuple[str, ...] = ('true', 'yes', '1'), false_values: tuple[str, ...] = ('false', 'no', '0')) -> None
```

Explicit generic value normalization controls.

### `NormalizationTarget` (value)


Type alias.

### `NormalizedCell` (class)

```python
NormalizedCell(*, column_name: NonEmptyString, original_value: ExcelPatchScalar = None, normalized_value: ExcelPatchScalar = None, source: document_sdk.core.models.ExcelSourceReference) -> None
```

One normalized table cell with source traceability.

### `NormalizedRow` (class)

```python
NormalizedRow(*, row_number: ExcelRowNumber, cells: tuple[document_sdk.excel.models.NormalizedCell, ...]) -> None
```

One normalized table row.

### `NormalizedValueResult` (class)

```python
NormalizedValueResult(*, original_value: ExcelPatchScalar = None, normalized_value: ExcelPatchScalar = None, target_type: Literal['auto', 'string', 'integer', 'decimal', 'percentage', 'date', 'datetime', 'boolean'], warnings: tuple[NonEmptyString, ...] = ()) -> None
```

Original and normalized representations of one scalar.

### `PreservationItem` (class)

```python
PreservationItem(*, feature: NonEmptyString, present: bool, status: Literal['SAFE', 'SAFE_WITH_WARNINGS', 'UNSUPPORTED'], disposition: Literal['guaranteed_preserved', 'expected_preserved', 'present_untouched', 'possible_loss', 'unsupported'], details: NonEmptyString) -> None
```

One deterministic preservation classification.

### `PreservationOperation` (value)


Type alias.

### `RowDimensionModification` (class)

```python
RowDimensionModification(*, sheet_name: WorksheetName, start_row: ExcelRowNumber, end_row: ExcelRowNumber, old_height: Annotated[float | None, Gt(gt=0)] = None, new_height: Annotated[float | None, Gt(gt=0)] = None, old_hidden: bool, new_hidden: bool, source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified worksheet row-dimension modification.

### `RowDimensionPatch` (class)

```python
RowDimensionPatch(*, sheet_name: WorksheetName, start_row: ExcelRowNumber, end_row: ExcelRowNumber | None = None, height: Annotated[float | None, Gt(gt=0), Le(le=409.5)] = None, clear_height: bool = False, hidden: bool | None = None) -> None
```

One bounded worksheet row-dimension patch.

### `RowHeightFeature` (class)

```python
RowHeightFeature(*, row: ExcelRowNumber, height: Annotated[float, Gt(gt=0)]) -> None
```

One explicitly configured worksheet row height.

### `SheetDiff` (class)

```python
SheetDiff(*, sheet_name: NonEmptyString, cell_diffs: tuple[document_sdk.excel.models.CellDiff, ...] = (), feature_diffs: tuple[document_sdk.excel.models.FeatureDiff, ...] = ()) -> None
```

All bounded differences for one worksheet.

### `SheetRangeSelection` (class)

```python
SheetRangeSelection(*, sheet_name: NonEmptyString, cell_range: NonEmptyString) -> None
```

Optional workbook comparison range for one sheet.

### `SheetVisibility` (value)


Type alias.

### `SheetWriteRequest` (class)

```python
SheetWriteRequest(*, name: NonEmptyString, cells: tuple[document_sdk.core.models.CellWriteRequest, ...] = ()) -> None
```

One worksheet to create in a workbook.

### `TableColumnPatch` (class)

```python
TableColumnPatch(*, column_id: Annotated[int, Ge(ge=1), Le(le=16384)], name: NonEmptyString, totals_row_function: Optional[Literal['average', 'count', 'countNums', 'custom', 'max', 'min', 'none', 'stdDev', 'sum', 'var']] = None) -> None
```

One ordered table-column identity in a structural table patch.

### `TableDetectionOptions` (class)

```python
TableDetectionOptions(*, min_rows: Annotated[int, Gt(gt=0), Le(le=1048576)] = 2, min_columns: Annotated[int, Gt(gt=0), Le(le=16384)] = 2, max_blank_rows: Annotated[int, Ge(ge=0), Lt(lt=1048576)] = 0, max_blank_columns: Annotated[int, Ge(ge=0), Lt(lt=16384)] = 1, header_scan_rows: Annotated[int, Gt(gt=0), Le(le=1048576)] = 3, minimum_density: Annotated[float, Gt(gt=0), Le(le=1)] = 0.2, max_cells: Annotated[int, Gt(gt=0)] = 100000) -> None
```

Deterministic thresholds for table-region candidates.

### `TableRangeModification` (class)

```python
TableRangeModification(*, sheet_name: WorksheetName, table_name: NonEmptyString, old_range: NonEmptyString, new_range: NonEmptyString, source: document_sdk.core.models.ExcelSourceReference, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified existing-table range change.

### `TableRangePatch` (class)

```python
TableRangePatch(*, sheet_name: WorksheetName, table_name: NonEmptyString, cell_range: NonEmptyString, columns: Annotated[tuple[document_sdk.excel.models.TableColumnPatch, ...] | None, MaxLen(max_length=16384)] = None) -> None
```

Resize one existing table and optionally replace its column identities.

### `TableRegionCandidate` (class)

```python
TableRegionCandidate(*, cell_range: NonEmptyString, header_row_candidates: tuple[ExcelRowNumber, ...], data_start_row: ExcelRowNumber | None, data_end_row: ExcelRowNumber | None, non_empty_cell_count: Annotated[int, Gt(gt=0)], non_empty_density: Annotated[float, Gt(gt=0), Le(le=1)], merged_header_ranges: tuple[str, ...] = (), score: Annotated[float, Ge(ge=0), Le(le=1)], warnings: tuple[NonEmptyString, ...] = (), source: document_sdk.core.models.ExcelSourceReference) -> None
```

Evidence-backed deterministic table-region candidate.

### `TableSchema` (class)

```python
TableSchema(*, columns: Annotated[tuple[document_sdk.excel.models.ColumnSchema, ...], MinLen(min_length=1)], header_row: ExcelRowNumber, allow_extra_columns: bool = True, require_unique_rows: bool = False) -> None
```

Generic table schema without customer business rules.

### `TableValidationResult` (class)

```python
TableValidationResult(*, valid: bool, table_schema: document_sdk.excel.models.TableSchema, rows: tuple[document_sdk.excel.models.NormalizedRow, ...], issues: tuple[document_sdk.excel.models.ValidationIssue, ...], source_file: document_sdk.core.models.FileDescriptor, sheet_name: NonEmptyString) -> None
```

Normalized rows and deterministic generic schema issues.

### `UnsupportedSheetFeature` (class)

```python
UnsupportedSheetFeature(*, name: WorksheetName, sheet_type: Literal['chartsheet', 'dialog_sheet', 'macro_sheet', 'unknown'], visibility: SheetVisibility) -> None
```

A non-worksheet sheet reported without backend objects.

### `UnsupportedWorkbookFeatureError` (exception)


Raised for a specifically unsupported workbook feature request.

### `ValidationIssue` (class)

```python
ValidationIssue(*, code: NonEmptyString, message: NonEmptyString, severity: Literal['error', 'warning'] = 'error', column_name: str | None = None, source: document_sdk.core.models.ExcelSourceReference, original_value: ExcelPatchScalar = None, normalized_value: ExcelPatchScalar = None) -> None
```

One generic validation issue at a traceable source cell.

### `WorkbookComparisonOptions` (class)

```python
WorkbookComparisonOptions(*, selected_sheets: tuple[NonEmptyString, ...] = (), selected_ranges: tuple[document_sdk.excel.models.SheetRangeSelection, ...] = (), ignore_empty_cells: bool = True, ignore_style: bool = False, ignore_formula_cache: bool = False, value_normalization: Literal['none', 'trim', 'casefold'] = 'none', max_differences: Annotated[int, Gt(gt=0)] = 10000, max_cells: Annotated[int, Gt(gt=0)] = 1000000) -> None
```

Bounds and ignore controls for workbook comparison.

### `WorkbookDefaultStyleModification` (class)

```python
WorkbookDefaultStyleModification(*, old_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], new_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], changed_components: Annotated[tuple[Literal['font', 'fill', 'border', 'alignment', 'number_format', 'named_style'], ...], MinLen(min_length=1), MaxLen(max_length=6)], source_file_id: NonEmptyString, output_file_id: NonEmptyString) -> None
```

One verified workbook default cell-style modification.

### `WorkbookDefaultStylePatch` (class)

```python
WorkbookDefaultStylePatch(*, font: document_sdk.excel.models.CellFontPatch | None = None, fill: document_sdk.excel.models.CellPatternFillPatch | None = None, border: document_sdk.excel.models.CellBorderPatch | None = None, alignment: document_sdk.excel.models.CellAlignmentPatch | None = None, number_format: ExcelNumberFormatCode | None = None, named_style: NonEmptyString | None = None) -> None
```

Complete format components for the workbook default cell style.

### `WorkbookDiff` (class)

```python
WorkbookDiff(*, old_file: document_sdk.core.models.FileDescriptor, new_file: document_sdk.core.models.FileDescriptor, sheets_added: tuple[NonEmptyString, ...] = (), sheets_removed: tuple[NonEmptyString, ...] = (), sheet_diffs: tuple[document_sdk.excel.models.SheetDiff, ...] = (), feature_diffs: tuple[document_sdk.excel.models.FeatureDiff, ...] = (), difference_count: Annotated[int, Ge(ge=0)], truncated: bool) -> None
```

Bounded, serializable workbook comparison.

### `WorkbookFeatureInventory` (class)

```python
WorkbookFeatureInventory(*, file: document_sdk.core.models.FileDescriptor, workbook_type: WorkbookType, sheet_names: tuple[WorksheetName, ...], worksheet_count: Annotated[int, Ge(ge=0)], worksheets: tuple[document_sdk.excel.models.WorksheetFeatureInventory, ...] = (), chartsheet_count: Annotated[int, Ge(ge=0)] = 0, chartsheets: tuple[document_sdk.excel.models.ChartsheetFeatureInventory, ...] = (), macro_sheet_count: Annotated[int, Ge(ge=0)] = 0, macro_sheets: tuple[document_sdk.excel.models.MacroSheetFeatureInventory, ...] = (), unsupported_sheets: tuple[document_sdk.excel.models.UnsupportedSheetFeature, ...] = (), defined_names: tuple[document_sdk.excel.models.DefinedNameFeature, ...] = (), external_link_count: Annotated[int, Ge(ge=0)], calculation_mode: Optional[Literal['auto', 'autoNoTable', 'manual']] = None, vba_project_present: bool, workbook_protection_present: bool, active_x_count: Annotated[int, Ge(ge=0)], unknown_package_parts: tuple[str, ...] = ()) -> None
```

Workbook and worksheet feature facts used for preservation decisions.

### `WorkbookModificationResult` (class)

```python
WorkbookModificationResult(*, source_file: document_sdk.core.models.FileDescriptor, output_file: document_sdk.core.models.FileDescriptor, changes: tuple[document_sdk.excel.models.CellModification, ...] = (), format_changes: tuple[document_sdk.excel.models.CellFormatModification, ...] = (), existing_cell_format_range_changes: tuple[document_sdk.excel.models.ExistingCellFormatRangeModification, ...] = (), default_style_change: document_sdk.excel.models.WorkbookDefaultStyleModification | None = None, sheet_creations: tuple[document_sdk.excel.models.WorksheetCreationModification, ...] = (), sheet_order_change: document_sdk.excel.models.WorkbookSheetOrderModification | None = None, freeze_pane_changes: tuple[document_sdk.excel.models.FreezePaneModification, ...] = (), auto_filter_changes: tuple[document_sdk.excel.models.AutoFilterModification, ...] = (), merged_range_changes: tuple[document_sdk.excel.models.MergedRangeModification, ...] = (), table_range_changes: tuple[document_sdk.excel.models.TableRangeModification, ...] = (), defined_name_changes: tuple[document_sdk.excel.models.DefinedNameModification, ...] = (), conditional_formatting_changes: tuple[document_sdk.excel.models.ConditionalFormattingModification, ...] = (), data_validation_changes: tuple[document_sdk.excel.models.DataValidationModification, ...] = (), hyperlink_changes: tuple[document_sdk.excel.models.HyperlinkModification, ...] = (), legacy_comment_changes: tuple[document_sdk.excel.models.LegacyCommentsModification, ...] = (), column_changes: tuple[document_sdk.excel.models.ColumnDimensionModification, ...] = (), row_changes: tuple[document_sdk.excel.models.RowDimensionModification, ...] = (), structural_changes: tuple[document_sdk.excel.models.WorkbookStructuralModification, ...] = (), external_links_removed: Annotated[int, Ge(ge=0)] = 0, preservation: document_sdk.excel.models.WorkbookPreservationReport, warnings: tuple[NonEmptyString, ...] = (), source_unchanged: bool, vba_preserved: bool | None = None) -> None
```

Verified atomic workbook modification or content-identical no-op evidence.

### `WorkbookNamedStylePatch` (class)

```python
WorkbookNamedStylePatch(*, name: NonEmptyString, builtin_id: Annotated[int | None, Ge(ge=0), Le(le=255)] = None, font: document_sdk.excel.models.CellFontPatch, fill: document_sdk.excel.models.CellPatternFillPatch, border: document_sdk.excel.models.CellBorderPatch, alignment: document_sdk.excel.models.CellAlignmentPatch, number_format: ExcelNumberFormatCode) -> None
```

One deterministic named-style definition imported before use.

### `WorkbookPatchRequest` (class)

```python
WorkbookPatchRequest(*, cells: tuple[document_sdk.excel.models.CellPatch, ...] = (), formats: Annotated[tuple[document_sdk.excel.models.CellFormatPatch, ...], MaxLen(max_length=100000)] = (), existing_cell_format_ranges: Annotated[tuple[document_sdk.excel.models.ExistingCellFormatRangePatch, ...], MaxLen(max_length=1000)] = (), default_style: document_sdk.excel.models.WorkbookDefaultStylePatch | None = None, named_styles: Annotated[tuple[document_sdk.excel.models.WorkbookNamedStylePatch, ...], MaxLen(max_length=1000)] = (), create_sheets: Annotated[tuple[document_sdk.excel.models.WorksheetCreatePatch, ...], MaxLen(max_length=1000)] = (), delete_sheets: Annotated[tuple[document_sdk.excel.models.WorksheetDeletePatch, ...], MaxLen(max_length=1000)] = (), structural_insertions: Annotated[tuple[document_sdk.excel.models.WorksheetStructuralInsertionPatch, ...], MaxLen(max_length=1000)] = (), drawing_removals: Annotated[tuple[document_sdk.excel.models.WorksheetDrawingRemovalPatch, ...], MaxLen(max_length=1000)] = (), image_additions: Annotated[tuple[document_sdk.excel.models.WorksheetImagePatch, ...], MaxLen(max_length=1000)] = (), external_link_removals: Annotated[tuple[document_sdk.excel.models.ExternalLinkRemovalPatch, ...], MaxLen(max_length=10000)] = (), sheet_order: document_sdk.excel.models.WorkbookSheetOrderPatch | None = None, freeze_panes: Annotated[tuple[document_sdk.excel.models.FreezePanePatch, ...], MaxLen(max_length=1000)] = (), auto_filters: Annotated[tuple[document_sdk.excel.models.AutoFilterPatch, ...], MaxLen(max_length=1000)] = (), merged_ranges: Annotated[tuple[document_sdk.excel.models.MergedRangePatch, ...], MaxLen(max_length=100000)] = (), table_ranges: Annotated[tuple[document_sdk.excel.models.TableRangePatch, ...], MaxLen(max_length=10000)] = (), defined_names: Annotated[tuple[document_sdk.excel.models.DefinedNamePatch, ...], MaxLen(max_length=100000)] = (), conditional_formatting: Annotated[tuple[document_sdk.excel.models.WorksheetConditionalFormattingPatch, ...], MaxLen(max_length=1000)] = (), data_validations: Annotated[tuple[document_sdk.excel.models.WorksheetDataValidationPatch, ...], MaxLen(max_length=1000)] = (), hyperlinks: Annotated[tuple[document_sdk.excel.models.WorksheetHyperlinkPatch, ...], MaxLen(max_length=1000)] = (), legacy_comments: Annotated[tuple[document_sdk.excel.models.WorksheetLegacyCommentsPatch, ...], MaxLen(max_length=1000)] = (), named_ranges: tuple[document_sdk.excel.models.NamedRangePatch, ...] = (), column_dimensions: Annotated[tuple[document_sdk.excel.models.ColumnDimensionPatch, ...], MaxLen(max_length=100000)] = (), row_dimensions: Annotated[tuple[document_sdk.excel.models.RowDimensionPatch, ...], MaxLen(max_length=100000)] = (), remove_unreferenced_external_links: bool = False, output_file_id: NonEmptyString | None = None) -> None
```

Typed changes for safe workbook or template patching.

### `WorkbookPreservationError` (exception)

```python
WorkbookPreservationError(*, operation: str, unsupported_features: tuple[str, ...]) -> None
```

Raised when strict preservation rejects present workbook features.

### `WorkbookPreservationReport` (class)

```python
WorkbookPreservationReport(*, file: document_sdk.core.models.FileDescriptor, operation: Literal['patch', 'template_fill', 'rewrite'], overall_status: Literal['SAFE', 'SAFE_WITH_WARNINGS', 'UNSUPPORTED'], items: Annotated[tuple[document_sdk.excel.models.PreservationItem, ...], MinLen(min_length=1)], warnings: tuple[NonEmptyString, ...] = ()) -> None
```

Preservation assessment for a selected workbook operation.

### `WorkbookSemanticDetails` (class)

```python
WorkbookSemanticDetails(*, contract_version: Literal['excel-semantic-details/v1'] = 'excel-semantic-details/v1', file: document_sdk.core.models.FileDescriptor, package_parts: tuple[document_sdk.excel.semantic_details.ExcelPackagePartDetail, ...], relationships: tuple[document_sdk.excel.semantic_details.ExcelRelationshipDetail, ...], styles: tuple[document_sdk.excel.semantic_details.ExcelStyleDetail, ...], physical_cells: tuple[document_sdk.excel.semantic_details.ExcelPhysicalCellDetail, ...], comments: tuple[document_sdk.excel.semantic_details.ExcelCommentDetail, ...], defined_names: tuple[document_sdk.excel.semantic_details.ExcelDefinedNameDetail, ...], hyperlinks: tuple[document_sdk.excel.semantic_details.ExcelHyperlinkDetail, ...], tables: tuple[document_sdk.excel.semantic_details.ExcelTableDetail, ...], data_validations: tuple[document_sdk.excel.semantic_details.ExcelDataValidationDetail, ...], conditional_formatting: tuple[document_sdk.excel.semantic_details.ExcelConditionalFormattingDetail, ...], auto_filters: tuple[document_sdk.excel.semantic_details.ExcelAutoFilterDetail, ...], drawings: tuple[document_sdk.excel.semantic_details.ExcelDrawingDetail, ...], charts: tuple[document_sdk.excel.semantic_details.ExcelChartDetail, ...], rows: tuple[document_sdk.excel.semantic_details.ExcelRowDetail, ...], columns: tuple[document_sdk.excel.semantic_details.ExcelColumnDetail, ...], views: tuple[document_sdk.excel.semantic_details.ExcelViewDetail, ...], page_print: tuple[document_sdk.excel.semantic_details.ExcelPagePrintDetail, ...], workbook_properties: tuple[document_sdk.excel.semantic_details.ExcelWorkbookPropertyDetail, ...], worksheet_properties: tuple[document_sdk.excel.semantic_details.ExcelWorksheetPropertyDetail, ...], additional_source: tuple[document_sdk.excel.semantic_details.ExcelAdditionalSourceDetail, ...], record_count: Annotated[int, Ge(ge=0)], text_character_count: Annotated[int, Ge(ge=0)], complete: Literal[True] = True) -> None
```

Bounded source-detail view for declared OOXML workbook record families.

### `WorkbookSheetOrderModification` (class)

```python
WorkbookSheetOrderModification(*, old_sheet_names: Annotated[tuple[WorksheetName, ...], MinLen(min_length=1)], new_sheet_names: Annotated[tuple[WorksheetName, ...], MinLen(min_length=1)], source_file_id: NonEmptyString, output_file_id: NonEmptyString) -> None
```

One verified package-level workbook sheet reordering.

### `WorkbookSheetOrderPatch` (class)

```python
WorkbookSheetOrderPatch(*, sheet_names: Annotated[tuple[WorksheetName, ...], MinLen(min_length=1), MaxLen(max_length=10000)]) -> None
```

A complete ordering of every existing workbook sheet.

### `WorkbookStructuralModification` (class)

```python
WorkbookStructuralModification(*, operation: Literal['insert_rows', 'insert_columns', 'delete_worksheet', 'remove_drawings', 'add_image', 'remove_external_link'], target: NonEmptyString, count: Annotated[int, Ge(ge=1), Le(le=100000)] = 1, source_file_id: NonEmptyString, output_file_id: NonEmptyString) -> None
```

One verified package-level workbook structural operation.

### `WorkbookType` (value)


Type alias.

### `WorkbookWriteRequest` (class)

```python
WorkbookWriteRequest(*, sheets: Annotated[tuple[document_sdk.core.models.SheetWriteRequest, ...], MinLen(min_length=1)]) -> None
```

A complete local workbook creation request.

### `WorksheetConditionalFormattingPatch` (class)

```python
WorksheetConditionalFormattingPatch(*, sheet_name: WorksheetName, blocks: Annotated[tuple[document_sdk.excel.models.ConditionalFormattingBlockPatch, ...], MaxLen(max_length=10000)] = ()) -> None
```

Explicit full replacement of one worksheet's conditional formatting.

### `WorksheetCreatePatch` (class)

```python
WorksheetCreatePatch(*, name: WorksheetName, index: Annotated[int, Ge(ge=0), Le(le=9999)], visibility: SheetVisibility = 'visible') -> None
```

One explicitly positioned worksheet creation request.

### `WorksheetCreationModification` (class)

```python
WorksheetCreationModification(*, sheet_name: WorksheetName, index: Annotated[int, Ge(ge=0), Le(le=9999)], visibility: SheetVisibility, output_source: document_sdk.core.models.ExcelSourceReference) -> None
```

One verified newly created worksheet in the output workbook.

### `WorksheetDataValidationPatch` (class)

```python
WorksheetDataValidationPatch(*, sheet_name: WorksheetName, rules: Annotated[tuple[document_sdk.excel.models.DataValidationRulePatch, ...], MaxLen(max_length=100000)] = ()) -> None
```

Explicit full replacement of one worksheet's standard validations.

### `WorksheetDeletePatch` (class)

```python
WorksheetDeletePatch(*, name: WorksheetName) -> None
```

Delete one existing worksheet and its owned package graph.

### `WorksheetDrawingRemovalPatch` (class)

```python
WorksheetDrawingRemovalPatch(*, sheet_name: WorksheetName) -> None
```

Remove all drawing objects owned by one worksheet.

### `WorksheetFeatureInventory` (class)

```python
WorksheetFeatureInventory(*, name: WorksheetName, visibility: SheetVisibility, freeze_panes: str | None = None, merged_ranges: tuple[str, ...] = (), row_heights: tuple[document_sdk.excel.models.RowHeightFeature, ...] = (), column_widths: tuple[document_sdk.excel.models.ColumnWidthFeature, ...] = (), print_area: tuple[str, ...] = (), print_title_rows: str | None = None, print_title_columns: str | None = None, page_orientation: Optional[Literal['portrait', 'landscape']] = None, hyperlinks: tuple[document_sdk.excel.models.LocatedWorkbookFeature, ...] = (), comments: tuple[document_sdk.excel.models.LocatedWorkbookFeature, ...] = (), data_validations: tuple[document_sdk.excel.models.LocatedWorkbookFeature, ...] = (), conditional_formats: tuple[document_sdk.excel.models.LocatedWorkbookFeature, ...] = (), tables: tuple[document_sdk.excel.models.ExcelTableFeature, ...] = (), formulas: tuple[document_sdk.excel.models.LocatedWorkbookFeature, ...] = (), hidden_rows: tuple[int, ...] = (), hidden_columns: tuple[str, ...] = (), drawing_count: Annotated[int, Ge(ge=0)], image_count: Annotated[int, Ge(ge=0)], chart_count: Annotated[int, Ge(ge=0)], styled_cell_count: Annotated[int, Ge(ge=0)], hyperlink_count: Annotated[int, Ge(ge=0)], comment_count: Annotated[int, Ge(ge=0)], data_validation_count: Annotated[int, Ge(ge=0)], conditional_formatting_count: Annotated[int, Ge(ge=0)], table_count: Annotated[int, Ge(ge=0)], formula_count: Annotated[int, Ge(ge=0)]) -> None
```

Serializable feature inventory for one worksheet.

### `WorksheetHyperlinkPatch` (class)

```python
WorksheetHyperlinkPatch(*, sheet_name: WorksheetName, links: Annotated[tuple[document_sdk.excel.models.HyperlinkRecordPatch, ...], MaxLen(max_length=100000)] = ()) -> None
```

Explicit full replacement of one worksheet's hyperlink set.

### `WorksheetImagePatch` (class)

```python
WorksheetImagePatch(*, sheet_name: WorksheetName, content_type: Literal['image/png', 'image/jpeg', 'image/gif'], data_base64: Annotated[str, MinLen(min_length=4), MaxLen(max_length=28000000)], sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], from_marker: document_sdk.excel.models.DrawingMarkerPatch, to_marker: document_sdk.excel.models.DrawingMarkerPatch, name: NonEmptyString = 'Picture') -> None
```

Add one bounded image at an explicit two-cell worksheet anchor.

### `WorksheetLegacyCommentsPatch` (class)

```python
WorksheetLegacyCommentsPatch(*, sheet_name: WorksheetName, comments: Annotated[tuple[document_sdk.excel.models.LegacyCommentRecordPatch, ...], MaxLen(max_length=100000)] = ()) -> None
```

Explicit full replacement of one worksheet's legacy comments.

### `WorksheetRow` (class)

```python
WorksheetRow(*, row_number: ExcelRowNumber, cells: Annotated[tuple[document_sdk.core.models.ExcelCell, ...], MinLen(min_length=1)]) -> None
```

One deterministic streamed worksheet row.

### `WorksheetStructuralInsertionPatch` (class)

```python
WorksheetStructuralInsertionPatch(*, sheet_name: WorksheetName, axis: Literal['row', 'column'], before: Annotated[int, Ge(ge=1), Le(le=1048576)], count: Annotated[int, Ge(ge=1), Le(le=1000)]) -> None
```

Insert bounded rows or columns before one worksheet position.

### `assess_workbook_preservation` (function)

```python
assess_workbook_preservation(path: 'Path', *, operation: 'PreservationOperation') -> 'WorkbookPreservationReport'
```

Assess feature-preservation risk for one planned workbook operation.

### `compare_workbooks` (function)

```python
compare_workbooks(old_path: 'Path', new_path: 'Path', *, options: 'WorkbookComparisonOptions | None' = None) -> 'WorkbookDiff'
```

Compare two local XLSX/XLSM workbooks within explicit generic bounds.

### `detect_table_regions` (function)

```python
detect_table_regions(path: 'Path', sheet_name: 'str', *, cell_range: 'str | None' = None, options: 'TableDetectionOptions | None' = None) -> 'tuple[TableRegionCandidate, ...]'
```

Return deterministic table candidates and their structural evidence.

### `inspect_workbook` (function)

```python
inspect_workbook(path: 'Path', *, package_limits: 'ExcelPackageLimits | None' = None) -> 'WorkbookInspection'
```

Inspect local XLSX/XLSM structure without returning backend objects.

Args:
    path: Local ``.xlsx`` or ``.xlsm`` path.
    package_limits: Optional finite OOXML expansion limits.

Returns:
    Workbook and worksheet inspection models.

### `inspect_workbook_features` (function)

```python
inspect_workbook_features(path: 'Path', *, package_limits: 'ExcelPackageLimits | None' = None) -> 'WorkbookFeatureInventory'
```

Return a serializable inventory for one local XLSX or XLSM workbook.

### `inspect_workbook_semantic_details` (function)

```python
inspect_workbook_semantic_details(path: 'Path', *, package_limits: 'ExcelPackageLimits | None' = None) -> 'WorkbookSemanticDetails'
```

Return bounded source details without changing sparse Excel read semantics.

The result contains one record for every validated package member and
relationship plus semantically named records for known workbook families.
Custom XML and extension nodes are returned as ordered structured facts;
raw XML and binary payloads are never embedded in the public result.

### `iter_non_empty_cells` (function)

```python
iter_non_empty_cells(path: 'Path', sheet_name: 'str', *, cell_range: 'str | None' = None, max_cells: 'int' = 1000000, batch_size: 'int' = 1000, formula_view: 'FormulaView' = 'both', package_limits: 'ExcelPackageLimits | None' = None) -> 'Iterator[ExcelCell]'
```

Stream represented non-empty cells in stable row-major order.

The configured limit counts yielded cells rather than the rectangular
distance between them, so sparse sheets remain sparse. Formula caches are
read from OOXML and are never calculated.

### `iter_rows` (function)

```python
iter_rows(path: 'Path', sheet_name: 'str', *, cell_range: 'str | None' = None, max_cells: 'int' = 1000000, max_rows: 'int' = 100000, batch_size: 'int' = 1000, include_empty: 'bool' = False, formula_view: 'FormulaView' = 'both', package_limits: 'ExcelPackageLimits | None' = None) -> 'Iterator[WorksheetRow]'
```

Stream worksheet rows with explicit cell and row safety bounds.

By default only rows and cells represented by non-empty OOXML values are
yielded. ``include_empty=True`` deliberately fills a bounded rectangle
after checking both limits before cell iteration.

### `normalize_value` (function)

```python
normalize_value(value: 'ExcelPatchScalar', *, options: 'NormalizationOptions | None' = None, target_type: 'NormalizationTarget' = 'auto') -> 'NormalizedValueResult'
```

Normalize one supported scalar without changing a workbook.

### `patch_workbook` (function)

```python
patch_workbook(source_path: 'Path', output_path: 'Path', request: 'WorkbookPatchRequest', *, strict_preservation: 'bool' = True, overwrite: 'bool' = False) -> 'WorkbookModificationResult'
```

Apply typed workbook patches through one owned staging transaction.

### `read_range` (function)

```python
read_range(path: 'Path', sheet_name: 'str', cell_range: 'str', *, max_cells: 'int' = 100000, formula_view: 'FormulaView' = 'both') -> 'WorksheetData'
```

Read non-empty cells from one exact, bounded worksheet range.

Empty cells are omitted, matching :class:`WorksheetData`. The returned
``used_range`` is the actual non-empty bounds within the requested range,
or ``None`` when the requested range contains no values. Formula text and
available cached values are preserved; formulas are never calculated.

Args:
    path: Local ``.xlsx`` or ``.xlsm`` path.
    sheet_name: Exact worksheet name.
    cell_range: Inclusive Excel cell or rectangular range.
    max_cells: Positive maximum requested rectangular cell count.
    formula_view: Return formula text, cached values, or both.

Returns:
    Normalized non-empty cells limited to cell_range.

Raises:
    ExcelCellLimitExceededError: If cell_range exceeds max_cells.

### `read_sheet` (function)

```python
read_sheet(path: 'Path', sheet_name: 'str', *, max_cells: 'int | None' = None, formula_view: 'FormulaView' = 'both') -> 'WorksheetData'
```

Read one worksheet with an optional rectangular cell-count limit.

Args:
    path: Local ``.xlsx`` or ``.xlsm`` path.
    sheet_name: Exact worksheet name.
    max_cells: Optional positive maximum for the non-empty used rectangle.
        ``None`` preserves the existing unlimited default behavior.
    formula_view: Return formula text, cached values, or both.

Returns:
    Normalized non-empty cells with source references.

Raises:
    ExcelCellLimitExceededError: If the used rectangle exceeds max_cells.

### `validate_table` (function)

```python
validate_table(data: 'WorksheetData', schema: 'TableSchema', *, normalization: 'NormalizationOptions | None' = None) -> 'TableValidationResult'
```

Validate worksheet data using only caller-provided generic rules.

### `write_workbook` (function)

```python
write_workbook(request: 'WorkbookWriteRequest', output_path: 'Path') -> 'WorkbookInspection'
```

Create, save, reopen, and inspect a local XLSX workbook.

Args:
    request: Strict workbook and addressed-cell creation data.
    output_path: Destination ending in ``.xlsx``.

Returns:
    Inspection of the successfully reopened output workbook.

## `document_sdk.extraction`


### `ConstraintValueType` (class)

```python
ConstraintValueType(*values)
```

Exact immutable value families supported by allowed-value constraints.

### `DocumentTypeStatus` (class)

```python
DocumentTypeStatus(*values)
```

Final eligibility state for schema-restricted document types.

### `ExtractionConfidenceSource` (class)

```python
ExtractionConfidenceSource(*values)
```

Provenance of one candidate confidence observation.

### `ExtractionSchema` (class)

```python
ExtractionSchema(*, schema_id: Annotated[str, MinLen(min_length=1)], schema_version: Annotated[str, MinLen(min_length=1)], fields: Annotated[tuple[document_sdk.extraction.models.FieldDefinition, ...], MinLen(min_length=1)], accepted_document_types: tuple[str, ...] = ()) -> None
```

A deterministic customer-supplied extraction schema.

### `ExtractionSchemaError` (exception)


Raised when an extraction request does not contain a valid schema.

### `ExtractionStrategy` (class)

```python
ExtractionStrategy(*values)
```

Explicit document-analysis routes used before local extraction.

### `ExtractionValueType` (class)

```python
ExtractionValueType(*values)
```

Supported provider-independent structured value families.

### `FieldConstraintValue` (class)

```python
FieldConstraintValue(*, value_type: document_sdk.extraction.models.ConstraintValueType, value: str | int | decimal.Decimal | bool | datetime.date | datetime.time | tuple[str, ...] | document_sdk.core.models.DocumentCurrencyValue | document_sdk.core.models.DocumentAddressValue) -> None
```

One explicitly typed, deeply immutable allowed value.

### `FieldConstraints` (class)

```python
FieldConstraints(*, allowed_values: tuple[document_sdk.extraction.models.FieldConstraintValue, ...] = (), minimum: decimal.Decimal | None = None, maximum: decimal.Decimal | None = None, minimum_length: Annotated[int | None, Ge(ge=0)] = None, maximum_length: Annotated[int | None, Ge(ge=0)] = None, pattern: str | None = None) -> None
```

Generic trusted caller constraints for one extracted value.

### `FieldDefinition` (class)

```python
FieldDefinition(*, name: Annotated[str, MinLen(min_length=1)], value_type: document_sdk.extraction.models.ExtractionValueType, required: bool = False, aliases: tuple[str, ...] = (), allow_multiple: bool = False, min_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, constraints: document_sdk.extraction.models.FieldConstraints = <factory>) -> None
```

One canonical business field and its generic extraction rules.

### `StructuredExtractionIncompleteError` (exception)

```python
StructuredExtractionIncompleteError(summary: 'StructuredExtractionIncompleteSummary') -> 'None'
```

Raised after a validated result is incomplete when fail-fast is enabled.

### `StructuredExtractionIncompleteSummary` (class)

```python
StructuredExtractionIncompleteSummary(*, schema_id: Annotated[str, MinLen(min_length=1)], schema_version: Annotated[str, MinLen(min_length=1)], document_type_status: document_sdk.extraction.models.DocumentTypeStatus, missing_required_fields: tuple[str, ...] = (), unresolved_required_fields: tuple[str, ...] = (), issue_category_counts: collections.abc.Mapping[str, int] = <factory>) -> None
```

Sanitized fail-fast evidence without document or candidate data.

### `StructuredExtractionIssue` (class)

```python
StructuredExtractionIssue(*, code: Annotated[str, MinLen(min_length=1)], category: Annotated[str, MinLen(min_length=1)], message: Annotated[str, MinLen(min_length=1)], severity: Literal['warning', 'error'], field_name: str | None = None, count: Annotated[int, Ge(ge=1)] = 1) -> None
```

One content-free extraction or validation issue.

### `StructuredExtractionOptions` (class)

```python
StructuredExtractionOptions(*, strategy: document_sdk.extraction.models.ExtractionStrategy = <ExtractionStrategy.HYBRID_EXISTING: 'hybrid_existing'>, pages: tuple[int, ...] | None = None, locale: str | None = None, features: tuple[document_sdk.ocr.models.DocumentAnalysisFeature, ...] = (), coerce_raw_values: bool = True, fail_on_incomplete: bool = False, local_ocr_quality_policy: document_sdk.core.local_ocr_quality.LocalOcrStructuredQualityPolicy | None = None) -> None
```

Explicit extraction, analysis, and conservative coercion options.

### `StructuredExtractionProviderRequiredError` (exception)


Raised when the selected extraction strategy requires a Provider.

### `StructuredExtractionResult` (class)

```python
StructuredExtractionResult(*, schema: document_sdk.extraction.models.ExtractionSchema, schema_id: Annotated[str, MinLen(min_length=1)], schema_version: Annotated[str, MinLen(min_length=1)], document: document_sdk.core.models.Document, fields: tuple[document_sdk.extraction.models.StructuredFieldResult, ...], accepted_document_types: tuple[str, ...] = (), document_type_status: document_sdk.extraction.models.DocumentTypeStatus = <DocumentTypeStatus.NOT_RESTRICTED: 'not_restricted'>, observed_document_types: tuple[str, ...] = (), matched_document_types: tuple[str, ...] = (), complete: bool, missing_required_fields: tuple[str, ...] = (), unresolved_required_fields: tuple[str, ...] = (), issues: tuple[document_sdk.extraction.models.StructuredExtractionIssue, ...] = (), warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = (), provider_usage: document_sdk.core.models.ProviderUsage | None = None, cloud_execution_attempt: document_sdk.core.models.CloudExecutionAttemptEvidence | None = None, local_ocr_quality_report: document_sdk.core.local_ocr_quality.LocalOcrQualityReport | None = None, local_ocr_preprocessing_report: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingReport | None = None) -> None
```

Complete document and final schema-resolution outcome.

### `StructuredFieldCandidate` (class)

```python
StructuredFieldCandidate(*, source_kind: Literal['analyzed_field', 'key_value_pair'], matched_name: str, match_kind: Literal['canonical', 'alias'], field: document_sdk.core.models.DocumentField, confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, confidence_source: document_sdk.extraction.models.ExtractionConfidenceSource = <ExtractionConfidenceSource.UNAVAILABLE: 'unavailable'>, confidence_usable_for_thresholds: bool = False, sources: tuple[SourceReference, ...] = (), elements: tuple[document_sdk.core.models.DocumentElementReference, ...] = (), document_type: str | None = None) -> None
```

One provider-independent field candidate with complete evidence.

### `StructuredFieldResult` (class)

```python
StructuredFieldResult(*, name: Annotated[str, MinLen(min_length=1)], definition: document_sdk.extraction.models.FieldDefinition, status: Literal['found', 'missing', 'ambiguous', 'invalid', 'low_confidence', 'raw_only'], selected: tuple[document_sdk.extraction.models.StructuredFieldCandidate, ...] = (), candidates: tuple[document_sdk.extraction.models.StructuredFieldCandidate, ...] = (), issues: tuple[document_sdk.extraction.models.StructuredExtractionIssue, ...] = ()) -> None
```

Final deterministic resolution state for one schema field.

### `analyze_pdf_structured` (function)

```python
analyze_pdf_structured(path: 'Path', schema: 'ExtractionSchema', *, ocr_provider: 'OcrProvider | None' = None, options: 'StructuredExtractionOptions | None' = None, limits: 'PdfProcessingLimits | None' = None) -> 'StructuredExtractionResult'
```

Analyze one PDF through an explicit strategy and return final fields.

### `extract_structured_fields` (function)

```python
extract_structured_fields(document: 'Document', schema: 'ExtractionSchema', *, options: 'StructuredExtractionOptions | None' = None) -> 'StructuredExtractionResult'
```

Resolve a schema against normalized analyzed fields and key-value pairs.

## `document_sdk.files`


### `calculate_sha256` (function)

```python
calculate_sha256(path: pathlib.Path, *, chunk_size: int = 1048576) -> document_sdk.core.models.FileFingerprint
```

Calculate SHA-256 without loading the whole file into memory.

Args:
    path: Local regular file to hash.
    chunk_size: Maximum number of bytes read per iteration.

Returns:
    The lowercase SHA-256 fingerprint.

Raises:
    ValueError: If ``chunk_size`` is not positive.
    FileAccessError: If the path is not an accessible regular file.

### `inspect_file` (function)

```python
inspect_file(path: pathlib.Path) -> document_sdk.core.models.FileDescriptor
```

Inspect a supported local file without exposing its absolute path.

Args:
    path: Path to a supported PDF, image, DOCX, XLSX, or XLSM regular file.

Returns:
    A safe descriptor whose file identity is its SHA-256 digest.

Raises:
    FileAccessError: If the path is missing, not a file, or cannot be read.
    UnsupportedFileError: If the file extension is unsupported.

## `document_sdk.image`


### `DocumentNormalizationOptions` (class)

```python
DocumentNormalizationOptions(*, frame_number: Annotated[int, Ge(ge=1)] = 1, normalize_orientation: bool = True, grayscale: bool = True, deskew: bool = False, perspective_corners: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]] | None = None, auto_perspective: bool = False, minimum_corner_confidence: Annotated[float, Ge(ge=0), Le(le=1)] = 0.8, threshold: Literal['none', 'global', 'adaptive'] = 'none', global_threshold: Annotated[int, Ge(ge=0), Le(le=255)] = 127, normalize_background: bool = False, denoise_strength: Annotated[int, Ge(ge=0), Le(le=20)] = 0, remove_small_noise: bool = False, crop_blank_margins: bool = False, enhance_lines: bool = False, output_format: ImageFormat = 'PNG') -> None
```

Explicit OpenCV document-scan normalization operations.

### `DocumentNormalizationResult` (class)

```python
DocumentNormalizationResult(*, image: document_sdk.image.models.EncodedImage, transformation_matrix: tuple[tuple[float, float, float], ...], applied_operations: tuple[str, ...], perspective_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, warnings: tuple[str, ...] = ()) -> None
```

Normalized scan and applied geometric evidence.

### `EncodedImage` (class)

```python
EncodedImage(*, data: Annotated[bytes, MinLen(min_length=1)], format: ImageFormat, mime_type: ImageMimeType, width: Annotated[int, Gt(gt=0)], height: Annotated[int, Gt(gt=0)], mode: Annotated[str, MinLen(min_length=1)], source: document_sdk.core.models.ImageSourceReference) -> None
```

Backend-neutral encoded image bytes and source traceability.

### `ImageAlignmentError` (exception)


Raised when bounded alignment has insufficient geometric evidence.

### `ImageAlignmentEvidence` (class)

```python
ImageAlignmentEvidence(*, mode: AlignmentMode, transformation_matrix: tuple[tuple[float, ...], ...], matched_feature_count: Annotated[int, Ge(ge=0)], inlier_count: Annotated[int, Ge(ge=0)], inlier_ratio: Annotated[float, Ge(ge=0), Le(le=1)], alignment_score: Annotated[float, Ge(ge=0)]) -> None
```

Serializable alignment evidence shared with comparison results.

### `ImageAlignmentOptions` (class)

```python
ImageAlignmentOptions(*, mode: AlignmentMode = 'translation', max_features: Annotated[int, Gt(gt=0), Le(le=10000)] = 1000, minimum_matches: Annotated[int, Gt(gt=0)] = 8, ransac_threshold: Annotated[float, Gt(gt=0)] = 3, include_aligned_image: bool = True, output_format: ImageFormat = 'PNG') -> None
```

Bounded deterministic alignment configuration.

### `ImageAlignmentResult` (class)

```python
ImageAlignmentResult(*, reference: document_sdk.core.models.ImageSourceReference, candidate: document_sdk.core.models.ImageSourceReference, evidence: document_sdk.image.models.ImageAlignmentEvidence, output_width: Annotated[int, Gt(gt=0)], output_height: Annotated[int, Gt(gt=0)], aligned_image: document_sdk.image.models.EncodedImage | None = None, warnings: tuple[str, ...] = ()) -> None
```

Deterministic geometric alignment result.

### `ImageComparisonOptions` (class)

```python
ImageComparisonOptions(*, align: document_sdk.image.models.ImageAlignmentOptions | None = None, color_mode: Literal['grayscale', 'color'] = 'grayscale', pixel_threshold: Annotated[int, Ge(ge=0), Le(le=255)] = 16, morphology_size: Annotated[int, Ge(ge=0), Le(le=31)] = 0, minimum_region_area: Annotated[int, Gt(gt=0)] = 1, max_difference_regions: Annotated[int, Gt(gt=0)] = 100, ignored_border: Annotated[int, Ge(ge=0)] = 0, alpha_mode: Literal['compare', 'ignore', 'composite_white'] = 'compare', visualization: Literal['mask', 'overlay', 'red_blue'] = 'overlay') -> None
```

Pixel-difference extraction configuration.

### `ImageComparisonResult` (class)

```python
ImageComparisonResult(*, reference: document_sdk.core.models.ImageSourceReference, candidate: document_sdk.core.models.ImageSourceReference, width: Annotated[int, Gt(gt=0)], height: Annotated[int, Gt(gt=0)], changed_pixel_count: Annotated[int, Ge(ge=0)], changed_pixel_ratio: Annotated[float, Ge(ge=0), Le(le=1)], difference_regions: tuple[document_sdk.image.models.ImageDifferenceRegion, ...], difference_mask: document_sdk.image.models.EncodedImage, visualization: document_sdk.image.models.EncodedImage, alignment: document_sdk.image.models.ImageAlignmentEvidence | None = None, warnings: tuple[str, ...] = ()) -> None
```

Objective visual differences without business classification.

### `ImageDifferenceRegion` (class)

```python
ImageDifferenceRegion(*, bounding_box: document_sdk.core.models.BoundingBox, pixel_area: Annotated[int, Gt(gt=0)]) -> None
```

One bounded connected visual-difference region.

### `ImageFrameInspection` (class)

```python
ImageFrameInspection(*, frame_number: Annotated[int, Ge(ge=1)], width: Annotated[int, Gt(gt=0)], height: Annotated[int, Gt(gt=0)], mode: NonEmptyString, pixel_count: Annotated[int, Gt(gt=0)], has_alpha: bool, exif_orientation: Optional[Annotated[int, FieldInfo(annotation=NoneType, required=True, metadata=[Ge(ge=1), Le(le=8)])]] = None, decode_verified: bool, source: document_sdk.core.models.ImageSourceReference) -> None
```

Normalized facts for one encoded image frame.

### `ImageInspection` (class)

```python
ImageInspection(*, file: document_sdk.core.models.FileDescriptor, format: Literal['PNG', 'JPEG', 'TIFF', 'BMP', 'WEBP'], mime_type: Literal['image/png', 'image/jpeg', 'image/tiff', 'image/bmp', 'image/webp'], frame_count: Annotated[int, Ge(ge=1)], animated: bool, frames: Annotated[tuple[document_sdk.core.models.ImageFrameInspection, ...], MinLen(min_length=1)], warnings: tuple[NonEmptyString, ...] = ()) -> None
```

Local image inspection facts without Pillow-owned objects.

### `ImagePreservationError` (exception)


Raised when strict image preservation cannot be guaranteed.

### `ImagePreservationItem` (class)

```python
ImagePreservationItem(*, feature: Annotated[str, MinLen(min_length=1)], present: bool, status: PreservationStatus, details: Annotated[str, MinLen(min_length=1)]) -> None
```

Evidence-based preservation status for one feature.

### `ImagePreservationReport` (class)

```python
ImagePreservationReport(*, source: document_sdk.core.models.FileDescriptor, target_format: ImageFormat, overall_status: PreservationStatus, items: tuple[document_sdk.image.models.ImagePreservationItem, ...], warnings: tuple[str, ...] = ()) -> None
```

Conservative preservation assessment for a requested transformation.

### `ImageProcessingLimits` (class)

```python
ImageProcessingLimits(*, max_frames: Annotated[int, Gt(gt=0)] = 100, max_pixels_per_frame: Annotated[int, Gt(gt=0)] = 25000000, max_total_pixels: Annotated[int, Gt(gt=0)] = 100000000, max_working_pixels: Annotated[int, Gt(gt=0)] = 50000000, max_output_bytes: Annotated[int, Gt(gt=0)] = 50000000, max_output_width: Annotated[int, Gt(gt=0)] = 20000, max_output_height: Annotated[int, Gt(gt=0)] = 20000) -> None
```

Explicit bounds applied before full image-frame decoding.

### `ImageQualityOptions` (class)

```python
ImageQualityOptions(*, frame_number: Annotated[int, Ge(ge=1)] = 1, near_black_level: Annotated[int, Ge(ge=0), Le(le=255)] = 5, near_white_level: Annotated[int, Ge(ge=0), Le(le=255)] = 250, blank_level: Annotated[int, Ge(ge=0), Le(le=255)] = 245, minimum_effective_dpi: Annotated[float, Gt(gt=0)] = 150, advanced: bool = False) -> None
```

Deterministic thresholds for objective quality evidence.

### `ImageQualityReport` (class)

```python
ImageQualityReport(*, source: document_sdk.core.models.ImageSourceReference, width: Annotated[int, Gt(gt=0)], height: Annotated[int, Gt(gt=0)], brightness: Annotated[float, Ge(ge=0), Le(le=255)], contrast: Annotated[float, Ge(ge=0)], black_clipping_ratio: Annotated[float, Ge(ge=0), Le(le=1)], white_clipping_ratio: Annotated[float, Ge(ge=0), Le(le=1)], near_blank_ratio: Annotated[float, Ge(ge=0), Le(le=1)], entropy: Annotated[float, Ge(ge=0)], effective_dpi: tuple[float, float] | None = None, alpha_coverage: Annotated[float, Ge(ge=0), Le(le=1)], blur_score: Annotated[float | None, Ge(ge=0)] = None, edge_density: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, estimated_noise: Annotated[float | None, Ge(ge=0)] = None, skew_angle_candidate: float | None = None, skew_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, background_uniformity: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, warnings: tuple[str, ...] = ()) -> None
```

Objective Pillow metrics plus optional OpenCV evidence.

### `ImageSimilarityOptions` (class)

```python
ImageSimilarityOptions(*, frame_number: Annotated[int, Ge(ge=1)] = 1, threshold_method: Optional[Literal['average_hash', 'difference_hash', 'perceptual_hash', 'histogram']] = None, threshold: Annotated[float | None, Ge(ge=0)] = None, include_histogram: bool = True, include_perceptual_hash: bool = False) -> None
```

Explicit similarity methods and optional caller threshold.

### `ImageSimilarityResult` (class)

```python
ImageSimilarityResult(*, reference: document_sdk.core.models.ImageSourceReference, candidate: document_sdk.core.models.ImageSourceReference, exact_file_sha_equal: bool, exact_decoded_pixels_equal: bool, normalized_pixels_equal: bool, average_hash_reference: str, average_hash_candidate: str, average_hash_distance: Annotated[int, Ge(ge=0)], difference_hash_reference: str, difference_hash_candidate: str, difference_hash_distance: Annotated[int, Ge(ge=0)], perceptual_hash_reference: str | None = None, perceptual_hash_candidate: str | None = None, perceptual_hash_distance: Annotated[int | None, Ge(ge=0)] = None, histogram_similarity: Annotated[float | None, Ge(ge=-1), Le(le=1)] = None, threshold_method: str | None = None, threshold: float | None = None, threshold_met: bool | None = None, warnings: tuple[str, ...] = ()) -> None
```

Multiple clearly labeled duplicate/similarity evidence methods.

### `ImageTransformRequest` (class)

```python
ImageTransformRequest(*, frame_number: Annotated[int | None, Ge(ge=1)] = None, preserve_all_frames: bool = False, normalize_orientation: bool = False, rotation_degrees: Annotated[float, Ge(ge=-360), Le(le=360)] = 0, flip_horizontal: bool = False, flip_vertical: bool = False, crop: document_sdk.core.models.BoundingBox | None = None, resize_width: Annotated[int | None, Gt(gt=0)] = None, resize_height: Annotated[int | None, Gt(gt=0)] = None, preserve_aspect_ratio: bool = True, output_mode: ImageColorMode | None = None, background_rgb: tuple[int, int, int] | None = None, output_format: ImageFormat, quality: Annotated[int, Ge(ge=1), Le(le=100)] = 90, tiff_compression: Literal['raw', 'tiff_lzw', 'tiff_adobe_deflate'] = 'tiff_lzw', preserve_dpi: bool = True, dpi: tuple[float, float] | None = None, preserve_icc_profile: bool = True, preserve_metadata: bool = False, strict_preservation: bool = False) -> None
```

Explicit deterministic operations applied in declaration order.

### `ImageTransformResult` (class)

```python
ImageTransformResult(*, source: document_sdk.core.models.FileDescriptor, output: document_sdk.core.models.FileDescriptor, frame_count: Annotated[int, Ge(ge=1)], preservation: document_sdk.image.models.ImagePreservationReport, warnings: tuple[str, ...] = ()) -> None
```

Verified atomic transform output.

### `PreservationStatus` (value)


Type alias.

### `align_images` (function)

```python
align_images(reference_path: 'Path', candidate_path: 'Path', options: 'ImageAlignmentOptions | None' = None, *, limits: 'ImageProcessingLimits | None' = None) -> 'ImageAlignmentResult'
```

Align deterministically without promising cross-version bit identity.

### `analyze_image_quality` (function)

```python
analyze_image_quality(path: 'Path', options: 'ImageQualityOptions | None' = None, *, limits: 'ImageProcessingLimits | None' = None) -> 'ImageQualityReport'
```

Return objective quality values without a universal verdict.

### `assess_image_preservation` (function)

```python
assess_image_preservation(path: 'Path', request: 'ImageTransformRequest', *, limits: 'ImageProcessingLimits | None' = None) -> 'ImagePreservationReport'
```

Assess evidence and risks for one explicit transform request.

### `compare_image_similarity` (function)

```python
compare_image_similarity(reference_path: 'Path', candidate_path: 'Path', options: 'ImageSimilarityOptions | None' = None, *, limits: 'ImageProcessingLimits | None' = None) -> 'ImageSimilarityResult'
```

Return labeled exact, hash, and optional histogram evidence.

### `compare_images` (function)

```python
compare_images(reference_path: 'Path', candidate_path: 'Path', options: 'ImageComparisonOptions | None' = None, *, limits: 'ImageProcessingLimits | None' = None) -> 'ImageComparisonResult'
```

Report thresholded visual differences and bounded regions.

### `inspect_image` (function)

```python
inspect_image(path: 'Path', *, limits: 'ImageProcessingLimits | None' = None, verify_decode: 'bool' = True) -> 'ImageInspection'
```

Inspect supported local image frames within explicit safety limits.

### `normalize_document_image` (function)

```python
normalize_document_image(path: 'Path', options: 'DocumentNormalizationOptions | None' = None, *, limits: 'ImageProcessingLimits | None' = None) -> 'DocumentNormalizationResult'
```

Apply explicitly configured OpenCV scan normalization.

### `read_image_frame` (function)

```python
read_image_frame(path: 'Path', frame_number: 'int' = 1, *, normalize_orientation: 'bool' = False, output_mode: 'ImageColorMode | None' = None, output_format: 'ImageFormat' = 'PNG', quality: 'int' = 90, limits: 'ImageProcessingLimits | None' = None) -> 'EncodedImage'
```

Read and safely encode exactly one selected image frame.

### `read_image_region` (function)

```python
read_image_region(path: 'Path', region: 'BoundingBox', frame_number: 'int' = 1, *, normalize_orientation: 'bool' = False, output_mode: 'ImageColorMode | None' = None, output_format: 'ImageFormat' = 'PNG', quality: 'int' = 90, limits: 'ImageProcessingLimits | None' = None) -> 'EncodedImage'
```

Read one normalized top-left region with source traceability.

### `transform_image` (function)

```python
transform_image(path: 'Path', request: 'ImageTransformRequest', output_path: 'Path', *, limits: 'ImageProcessingLimits | None' = None) -> 'ImageTransformResult'
```

Transform an image into a verified same-directory atomic output.

## `document_sdk.ocr`


### `AZURE_FALLBACK_PAYLOAD_POLICY_VERSION` (value)


str(object='') -> str

### `AZURE_PAGE_FALLBACK_ALGORITHM_VERSION` (value)


str(object='') -> str

### `LOCAL_OCR_PREPROCESSING_ALGORITHM_VERSION` (value)


str(object='') -> str

### `LOCAL_OCR_QUALITY_ALGORITHM_VERSION` (value)


str(object='') -> str

### `LOCAL_OCR_QUALITY_SELECTION_VERSION` (value)


str(object='') -> str

### `AzureDefaultCredentialResolver` (class)

```python
AzureDefaultCredentialResolver() -> 'None'
```

Construct a customer-owned DefaultAzureCredential only during resolve.

```python
AzureDefaultCredentialResolver.resolve(self) -> 'object'
```
Return the lazily constructed, resolver-owned Entra credential.

```python
AzureDefaultCredentialResolver.close(self) -> 'None'
```
Close and release the currently owned credential at most once.

### `AzureDocumentIntelligenceConfig` (class)

```python
AzureDocumentIntelligenceConfig(*, endpoint: str, model_id: NonEmptyString = 'prebuilt-layout', api_version: Literal['2024-11-30'] = '2024-11-30', polling_timeout_seconds: Annotated[int, Gt(gt=0), Le(le=3600)] = 120, max_input_bytes: Annotated[int, Gt(gt=0), Le(le=2000000000)] = 50000000, max_advanced_elements: Annotated[int, Gt(gt=0), Le(le=1000000)] = 20000, max_field_depth: Annotated[int, Gt(gt=0), Le(le=100)] = 20, max_field_count: Annotated[int, Gt(gt=0), Le(le=1000000)] = 10000, max_element_references: Annotated[int, Gt(gt=0), Le(le=1000000)] = 20000, max_content_characters: Annotated[int, Gt(gt=0), Le(le=100000000)] = 5000000, cloud_execution_policy: document_sdk.core.models.CloudExecutionPolicy = <factory>, transport_retry_total: Literal[0] = 0, provider_identity_version: Literal['azure-provider-identity-v2'] = 'azure-provider-identity-v2') -> None
```

One immutable customer-owned Azure Document Intelligence endpoint.

### `AzureDocumentIntelligenceProvider` (class)

```python
AzureDocumentIntelligenceProvider(*, context: 'ProviderContext') -> 'None'
```

Analyze one local PDF or image through an isolated Azure resource.

```python
AzureDocumentIntelligenceProvider.analyze(self, path: 'Path', *, options: 'OcrAnalysisOptions | None' = None) -> 'ProcessingResult[Document]'
```
Analyze one input after explicit direct-cloud authorization.

### `AzureEnvironmentKeyCredentialResolver` (class)

```python
AzureEnvironmentKeyCredentialResolver(env_var_name: 'str') -> 'None'
```

Resolve one customer's Azure key lazily from a named environment variable.

```python
AzureEnvironmentKeyCredentialResolver.resolve(self) -> 'object'
```
Return a fresh AzureKeyCredential without retaining the key.

### `AzureFallbackAttemptEvidence` (class)

```python
AzureFallbackAttemptEvidence(*, source_kind: Literal['page', 'frame'], provider_invocation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, trigger_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary, provider_identity_summary: document_sdk.ocr.fallback_models.AzureFallbackProviderIdentity, requested_features: Annotated[tuple[document_sdk.ocr.models.DocumentAnalysisFeature, ...], MaxLen(max_length=7)] = (), query_field_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, completed_azure_usages: Annotated[tuple[document_sdk.core.models.ProviderUsage, ...], MaxLen(max_length=10000)] = (), current_attempt_usage: document_sdk.core.models.ProviderUsage | None = None, completed_cloud_execution_attempts: Annotated[tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...], MaxLen(max_length=10000)] = (), current_cloud_execution_attempt: document_sdk.core.models.CloudExecutionAttemptEvidence | None = None, prepared_pages: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), prepared_frames: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), invoked_pages: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), invoked_frames: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), prepared_payload_byte_counts: Annotated[tuple[Annotated[int, FieldInfo(annotation=NoneType, required=True, metadata=[Strict(strict=True), Ge(ge=0), Le(le=1000000000)])], ...], MaxLen(max_length=10000)] = (), payload_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, payload_byte_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000000)] = 0) -> None
```

Safe partial evidence retained when fallback does not complete.

### `AzureFallbackConfigurationError` (exception)

```python
AzureFallbackConfigurationError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when explicit fallback configuration is incomplete.

### `AzureFallbackError` (exception)

```python
AzureFallbackError(message: str, *, attempt_evidence: object | None = None) -> None
```

Base class for controlled Azure fallback failures.

### `AzureFallbackExecutionError` (exception)

```python
AzureFallbackExecutionError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when the Azure Provider fails at the fallback boundary.

### `AzureFallbackInvalidResultError` (exception)

```python
AzureFallbackInvalidResultError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when Azure returns incomplete or inconsistent evidence.

### `AzureFallbackLimitError` (exception)

```python
AzureFallbackLimitError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised before fallback would exceed an explicit resource limit.

### `AzureFallbackMappingError` (exception)

```python
AzureFallbackMappingError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when isolated payload results cannot map to source indexes.

### `AzureFallbackPayloadError` (exception)

```python
AzureFallbackPayloadError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when an isolated payload cannot be created safely.

### `AzureFallbackProviderIdentity` (class)

```python
AzureFallbackProviderIdentity(*, provider_name: Literal['azure-document-intelligence'] = 'azure-document-intelligence', profile_id: Annotated[str, MinLen(min_length=1), MaxLen(max_length=128)], model_id: Annotated[str | None, MinLen(min_length=1), MaxLen(max_length=128)] = None, api_version: Annotated[str, MinLen(min_length=1), MaxLen(max_length=128)], provider_resource_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], identity_version: Literal['azure-provider-identity-v2'] = 'azure-provider-identity-v2') -> None
```

Safe immutable identity expected from the explicit Azure Provider.

### `AzureFallbackProviderTypeError` (exception)

```python
AzureFallbackProviderTypeError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when fallback receives a non-Azure Provider implementation.

### `AzureFallbackResumeIdentityMismatchError` (exception)

```python
AzureFallbackResumeIdentityMismatchError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when fallback identity differs from retained Resume evidence.

### `AzureFallbackSourceChangedError` (exception)

```python
AzureFallbackSourceChangedError(message: str, *, attempt_evidence: object | None = None) -> None
```

Raised when the caller's original source changes during fallback.

### `AzurePageFallbackPolicy` (class)

```python
AzurePageFallbackPolicy(*, expected_provider_identity: document_sdk.ocr.fallback_models.AzureFallbackProviderIdentity, max_fallback_pages_per_document: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 25, max_fallback_frames_per_document: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 25, max_fallback_inputs_per_document: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 25, max_fallback_operations_per_document: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 25, max_payload_bytes_per_input: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000000)] = 20000000, max_payload_bytes_per_document: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000000)] = 100000000, pdf_render_dpi: Annotated[int, Strict(strict=True), Ge(ge=72), Le(le=300)] = 144, azure_options: document_sdk.ocr.models.OcrAnalysisOptions = <factory>, algorithm_version: Literal['azure-page-fallback-v1'] = 'azure-page-fallback-v1', payload_policy_version: Literal['isolated-png-v1'] = 'isolated-png-v1') -> None
```

Explicit bounded opt-in policy for isolated Azure fallback inputs.

### `AzurePageFallbackReport` (class)

```python
AzurePageFallbackReport(*, status: document_sdk.ocr.fallback_models.AzurePageFallbackStatus, trigger_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary, policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], payload_policy_version: Literal['isolated-png-v1'] = 'isolated-png-v1', requested_features: Annotated[tuple[document_sdk.ocr.models.DocumentAnalysisFeature, ...], MaxLen(max_length=7)] = (), query_field_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, input_pages: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), input_frames: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), submitted_pages: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), submitted_frames: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), replaced_pages: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), replaced_frames: Annotated[tuple[int, ...], MaxLen(max_length=10000)] = (), reason_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=8)] = (), provider_invocation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, azure_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, paid_page_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, paid_frame_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, payload_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=10000)] = 0, payload_byte_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000000)] = 0, structured_recheck_performed: bool = False, structured_recheck_resolved: bool | None = None, structured_recheck_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary | None = None, algorithm_version: Literal['azure-page-fallback-v1'] = 'azure-page-fallback-v1', provider_identity_summary: document_sdk.ocr.fallback_models.AzureFallbackProviderIdentity | None = None) -> None
```

Content-free evidence for one completed explicit fallback attempt.

### `AzurePageFallbackResult` (class)

```python
AzurePageFallbackResult(*, document: document_sdk.core.models.Document, policy: document_sdk.ocr.fallback_models.AzurePageFallbackPolicy, report: document_sdk.ocr.fallback_models.AzurePageFallbackReport, azure_provider_usage: Annotated[tuple[document_sdk.core.models.ProviderUsage, ...], MaxLen(max_length=10000)] = (), cloud_execution_attempts: Annotated[tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...], MaxLen(max_length=10000)] = ()) -> None
```

Merged document with separate content-free Azure usage evidence.

### `AzurePageFallbackStatus` (class)

```python
AzurePageFallbackStatus(*values)
```

Successful Azure fallback outcomes.

### `DeterministicLocalOcrEngine` (class)

```python
DeterministicLocalOcrEngine(*, regions: 'Sequence[LocalOcrEngineRegion | LocalOcrRawRegion]' = (), identity: 'LocalOcrEngineIdentity | None' = None) -> 'None'
```

Content-independent deterministic Engine for routing evaluation.

```python
DeterministicLocalOcrEngine.recognize(self, image: 'LocalOcrImageInput') -> 'LocalOcrEngineResult'
```
Return the configured content-independent result.

### `DocumentAnalysisFeature` (class)

```python
DocumentAnalysisFeature(*values)
```

Explicit optional Provider analysis features.

### `LocalOcrEngine` (class)

```python
LocalOcrEngine(*args, **kwargs)
```

Stable caller-extensible in-memory Local OCR Engine contract.

```python
LocalOcrEngine.recognize(self, image: document_sdk.ocr.local_models.LocalOcrImageInput) -> document_sdk.ocr.local_models.LocalOcrEngineResult
```
Recognize one bounded runtime-only image without retaining it.

### `LocalOcrEngineIdentity` (class)

```python
LocalOcrEngineIdentity(*, engine_name: SafeIdentity, engine_version: SafeIdentity, model_id: SafeIdentity, languages: Annotated[tuple[SafeIdentity, ...], MinLen(min_length=1), MaxLen(max_length=32)] = ('und',), device_class: Literal['cpu'] = 'cpu', thread_safety: Literal['serialized', 'thread_safe'] = 'serialized') -> None
```

Stable sanitized identity used for results and Resume compatibility.

### `LocalOcrEngineIdentityError` (exception)


Raised when runtime Engine identity is incompatible with retained evidence.

### `LocalOcrEngineInitializationError` (exception)


Raised when an explicit Engine cannot be safely initialized.

### `LocalOcrEngineRegion` (class)

```python
LocalOcrEngineRegion(text: str, polygon: collections.abc.Sequence[tuple[float, float]], confidence: float, reading_order: int, language: str | None = None) -> None
```

Lightweight unvalidated Engine region created before SDK models.

### `LocalOcrEngineResult` (class)

```python
LocalOcrEngineResult(regions: collections.abc.Sequence[document_sdk.ocr.local_models.LocalOcrEngineRegion] = ()) -> None
```

Sized lightweight Engine result; generators are deliberately rejected.

### `LocalOcrError` (exception)


Base for controlled Local OCR failures.

### `LocalOcrExecutionError` (exception)


Raised when local Engine inference fails.

### `LocalOcrImageInput` (class)

```python
LocalOcrImageInput(*, width: Annotated[int, Gt(gt=0)], height: Annotated[int, Gt(gt=0)], mode: Literal['RGB', 'L'], pixels: Annotated[bytes, MinLen(min_length=1)], source_kind: Literal['image', 'pdf'], source_index: Annotated[int, Ge(ge=1)]) -> None
```

Runtime-only bounded decoded pixels passed to an explicit Engine.

### `LocalOcrInputQualityAssessment` (class)

```python
LocalOcrInputQualityAssessment(*, assessment_id: Annotated[str, _PydanticGeneralMetadata(pattern='^(pdf|image):[1-9][0-9]*$')], source_kind: Literal['pdf', 'image'], source_index: Annotated[int, Ge(ge=1)], character_count: Annotated[int, Ge(ge=0)], region_count: Annotated[int, Ge(ge=0)], confidence_weighted_character_count: Annotated[int, Ge(ge=0)], low_confidence_character_count: Annotated[int, Ge(ge=0)], suspicious_character_count: Annotated[int, Ge(ge=0)], region_area_numerator: Annotated[int, Ge(ge=0)], region_area_denominator: Annotated[int, Gt(gt=0)], mean_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, low_confidence_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, suspicious_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, region_area_ratio: Annotated[float, Ge(ge=0), Le(le=1)], decision: document_sdk.core.local_ocr_quality.LocalOcrQualityDecision, issue_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=6)] = ()) -> None
```

Content-free quality evidence for one submitted Local OCR input.

### `LocalOcrIntrinsicQualityPolicy` (class)

```python
LocalOcrIntrinsicQualityPolicy(*, minimum_characters_per_input: Annotated[int | None, Ge(ge=0)] = None, minimum_mean_confidence: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, low_confidence_threshold: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, maximum_low_confidence_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, maximum_suspicious_character_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, minimum_region_area_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None, include_private_use_characters: bool = False) -> None
```

Explicit intrinsic rules; optional thresholds are disabled by default.

### `LocalOcrInvalidResultError` (exception)


Raised when an Engine returns malformed or unsafe output.

### `LocalOcrLanguageProfile` (class)

```python
LocalOcrLanguageProfile(*values)
```

Canonical language profiles approved for Local OCR model selection.

### `LocalOcrLimitExceededError` (exception)

```python
LocalOcrLimitExceededError(*, limit_name: 'str', observed: 'int', maximum: 'int') -> 'None'
```

Raised before a configured Local OCR resource bound is exceeded.

### `LocalOcrModelSelectionError` (exception)


Raised before work when a Local OCR model selection is unsupported.

### `LocalOcrModelSelectionPolicy` (class)

```python
LocalOcrModelSelectionPolicy(*, language_profile: document_sdk.ocr.model_policy.LocalOcrLanguageProfile = <LocalOcrLanguageProfile.ZH_EN: 'zh_en'>, model_id: SafeCapabilityComponent = 'rapidocr-3.9.2-ppocrv6-small') -> None
```

Explicit path-free selection request for one approved Local OCR model.

### `LocalOcrModelUnavailableError` (exception)


Raised when caller-managed local model data is unavailable.

### `LocalOcrPreprocessingAttemptStatus` (class)

```python
LocalOcrPreprocessingAttemptStatus(*values)
```

Content-free status of one baseline or retry attempt.

### `LocalOcrPreprocessingAttemptSummary` (class)

```python
LocalOcrPreprocessingAttemptSummary(*, source_kind: Literal['image', 'pdf'], source_index: Annotated[int, Ge(ge=1)], profile: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingProfile, attempt_ordinal: Annotated[int, Ge(ge=0), Le(le=3)], status: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingAttemptStatus, operation_count: Annotated[int, Ge(ge=0), Le(le=1)], input_pixel_count: Annotated[int, Gt(gt=0)], output_pixel_count: Annotated[int, Ge(ge=0)], quality_assessment: document_sdk.core.local_ocr_quality.LocalOcrInputQualityAssessment | None = None, selected: bool = False, failure_category: Optional[Literal['profile', 'engine']] = None) -> None
```

Safe evidence for one baseline or preprocessing attempt.

### `LocalOcrPreprocessingConfigurationError` (exception)


The explicit preprocessing configuration is invalid.

### `LocalOcrPreprocessingError` (exception)


Base preprocessing failure.

### `LocalOcrPreprocessingExecutionError` (exception)


An in-memory preprocessing profile failed.

### `LocalOcrPreprocessingInputSummary` (class)

```python
LocalOcrPreprocessingInputSummary(*, source_kind: Literal['image', 'pdf'], source_index: Annotated[int, Ge(ge=1)], selected_profile: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingProfile, selected_attempt_ordinal: Annotated[int, Ge(ge=0), Le(le=3)], selection_reason: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingSelectionReason, original_decision: document_sdk.core.local_ocr_quality.LocalOcrQualityDecision, final_decision: document_sdk.core.local_ocr_quality.LocalOcrQualityDecision, attempt_count: Annotated[int, Ge(ge=1), Le(le=4)], preprocessing_pixel_count: Annotated[int, Ge(ge=0)], extra_operation_count: Annotated[int, Ge(ge=0), Le(le=3)]) -> None
```

Safe selected-attempt evidence for one source input.

### `LocalOcrPreprocessingLimitError` (exception)

```python
LocalOcrPreprocessingLimitError(*, limit_name: 'str', observed: 'int', maximum: 'int') -> 'None'
```

A preprocessing attempt or pixel limit was exceeded.

### `LocalOcrPreprocessingLimits` (class)

```python
LocalOcrPreprocessingLimits(*, max_extra_attempts_per_input: Annotated[int, Ge(ge=0), Le(le=3)] = 3, max_extra_attempts_per_document: Annotated[int, Ge(ge=0), Le(le=300)] = 30, max_preprocessing_pixels_per_input: Annotated[int, Gt(gt=0), Le(le=25000000)] = 25000000, max_total_preprocessing_pixels: Annotated[int, Gt(gt=0), Le(le=100000000)] = 100000000, max_working_pixels: Annotated[int, Gt(gt=0), Le(le=100000000)] = 100000000, max_profiles: Annotated[int, Ge(ge=1), Le(le=3)] = 3, max_profile_output_bytes: Annotated[int, Gt(gt=0), Le(le=75000000)] = 75000000) -> None
```

Finite hard-capped retry and in-memory pixel limits.

### `LocalOcrPreprocessingPolicy` (class)

```python
LocalOcrPreprocessingPolicy(*, enabled: bool = False, profiles: Annotated[tuple[document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingProfile, ...], MaxLen(max_length=3)] = (), stop_on_first_pass: Literal[True] = True, selection_policy_version: Literal['local-ocr-quality-selection-v1'] = 'local-ocr-quality-selection-v1', limits: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingLimits = <factory>) -> None
```

Explicit ordered preprocessing policy; disabled by default.

### `LocalOcrPreprocessingProfile` (class)

```python
LocalOcrPreprocessingProfile(*values)
```

Fixed geometry-preserving preprocessing profiles.

### `LocalOcrPreprocessingProfileCount` (class)

```python
LocalOcrPreprocessingProfileCount(*, profile: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingProfile, count: Annotated[int, Ge(ge=1)]) -> None
```

Stable selected-profile count without a mutable mapping.

### `LocalOcrPreprocessingReport` (class)

```python
LocalOcrPreprocessingReport(*, algorithm_version: Literal['local-ocr-preprocessing-v1'] = 'local-ocr-preprocessing-v1', selection_version: Literal['local-ocr-quality-selection-v1'] = 'local-ocr-quality-selection-v1', policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], policy: document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingPolicy, quality_policy: document_sdk.core.local_ocr_quality.LocalOcrIntrinsicQualityPolicy, source_kind: Literal['image', 'pdf'], input_indexes: Annotated[tuple[int, ...], MaxLen(max_length=100000)], input_summaries: Annotated[tuple[document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingInputSummary, ...], MaxLen(max_length=100000)], original_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary, final_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary, total_preprocessing_pixels: Annotated[int, Ge(ge=0)], total_extra_ocr_operations: Annotated[int, Ge(ge=0)], attempts: Annotated[tuple[document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingAttemptSummary, ...], MaxLen(max_length=100300)]) -> None
```

Content-free complete per-document preprocessing evidence.

### `LocalOcrPreprocessingSelectionError` (exception)


Candidate quality evidence could not be selected consistently.

### `LocalOcrPreprocessingSelectionReason` (class)

```python
LocalOcrPreprocessingSelectionReason(*values)
```

Stable reason for the selected local OCR candidate.

### `LocalOcrPreprocessingSummary` (class)

```python
LocalOcrPreprocessingSummary(*, algorithm_version: Literal['local-ocr-preprocessing-v1'] = 'local-ocr-preprocessing-v1', selection_version: Literal['local-ocr-quality-selection-v1'] = 'local-ocr-quality-selection-v1', policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], attempted_input_count: Annotated[int, Ge(ge=0)], not_needed_input_count: Annotated[int, Ge(ge=0)], preprocessing_attempted_input_count: Annotated[int, Ge(ge=0)], improved_input_count: Annotated[int, Ge(ge=0)], pass_after_preprocessing_input_count: Annotated[int, Ge(ge=0)], still_failed_input_count: Annotated[int, Ge(ge=0)], extra_attempt_count: Annotated[int, Ge(ge=0)], preprocessing_pixel_count: Annotated[int, Ge(ge=0)], extra_operation_count: Annotated[int, Ge(ge=0)], selected_profile_counts: Annotated[tuple[document_sdk.ocr.preprocessing_models.LocalOcrPreprocessingProfileCount, ...], MaxLen(max_length=4)] = (), source_page_count: Annotated[int, Ge(ge=0)], source_frame_count: Annotated[int, Ge(ge=0)]) -> None
```

Small durable preprocessing projection for Batch and Resume.

### `LocalOcrProcessingLimits` (class)

```python
LocalOcrProcessingLimits(*, max_width: Annotated[int, Gt(gt=0)] = 20000, max_height: Annotated[int, Gt(gt=0)] = 20000, max_pixels_per_input: Annotated[int, Gt(gt=0)] = 25000000, max_total_pixels: Annotated[int, Gt(gt=0)] = 100000000, max_pages: Annotated[int, Gt(gt=0)] = 100, max_frames: Annotated[int, Gt(gt=0)] = 100, max_source_pdf_pages: Annotated[int, Gt(gt=0), Le(le=100000)] = 1000, max_source_image_frames: Annotated[int, Gt(gt=0), Le(le=100000)] = 100, max_source_image_pixels_per_frame: Annotated[int, Gt(gt=0)] = 25000000, max_source_image_total_metadata_pixels: Annotated[int, Gt(gt=0)] = 100000000, max_regions_per_input: Annotated[int, Gt(gt=0)] = 2000, max_total_regions: Annotated[int, Gt(gt=0)] = 10000, max_lines_per_input: Annotated[int, Gt(gt=0)] = 2000, max_total_lines: Annotated[int, Gt(gt=0)] = 10000, max_words_per_input: Annotated[int, Gt(gt=0)] = 20000, max_total_words: Annotated[int, Gt(gt=0)] = 100000, max_text_characters_per_input: Annotated[int, Gt(gt=0)] = 500000, max_total_text_characters: Annotated[int, Gt(gt=0)] = 2000000, max_region_characters: Annotated[int, Gt(gt=0), Le(le=100000)] = 100000, max_operations: Annotated[int, Gt(gt=0)] = 100, max_concurrent_inferences: Annotated[int, Gt(gt=0)] = 1, pdf_render_dpi: Annotated[int, Ge(ge=1), Le(le=300)] = 144) -> None
```

Hard limits enforced around Local OCR inference and mapping.

### `LocalOcrProvider` (class)

```python
LocalOcrProvider(*, engine: 'LocalOcrEngine', profile_id: 'str' = 'local-default', limits: 'LocalOcrProcessingLimits | None' = None, quality_policy: 'LocalOcrIntrinsicQualityPolicy | None' = None, preprocessing_policy: 'LocalOcrPreprocessingPolicy | None' = None) -> 'None'
```

Run an explicit caller-supplied Local OCR Engine without credentials.

```python
LocalOcrProvider.analyze(self, path: 'Path', *, options: 'OcrAnalysisOptions | None' = None) -> 'ProcessingResult[Document]'
```
Stream selected image frames or PDF pages through runtime pixels.

### `LocalOcrQualityConfigurationError` (exception)


Raised before processing when Local OCR quality policy is incompatible.

### `LocalOcrQualityDecision` (class)

```python
LocalOcrQualityDecision(*values)
```

Provider-neutral decision for explicitly enabled Local OCR quality.

### `LocalOcrQualityEvaluationError` (exception)


Raised when quality evidence cannot be evaluated safely.

### `LocalOcrQualityIssueCode` (class)

```python
LocalOcrQualityIssueCode(*values)
```

Stable content-free Local OCR quality issue categories.

### `LocalOcrQualityIssueCount` (class)

```python
LocalOcrQualityIssueCount(*, code: document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, count: Annotated[int, Gt(gt=0)]) -> None
```

One deterministic non-zero issue-category count.

### `LocalOcrQualityPolicy` (class)

```python
LocalOcrQualityPolicy(*, intrinsic: document_sdk.core.local_ocr_quality.LocalOcrIntrinsicQualityPolicy = <factory>, structured: document_sdk.core.local_ocr_quality.LocalOcrStructuredQualityPolicy | None = None) -> None
```

Complete auditable Local OCR quality policy used by one report.

### `LocalOcrQualityReport` (class)

```python
LocalOcrQualityReport(*, algorithm_version: Literal['local-ocr-quality-v1'] = 'local-ocr-quality-v1', policy: document_sdk.core.local_ocr_quality.LocalOcrQualityPolicy, input_assessments: tuple[document_sdk.core.local_ocr_quality.LocalOcrInputQualityAssessment, ...] = (), structural_issue_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=2)] = (), required_field_count: Annotated[int, Ge(ge=0)] = 0, missing_required_field_count: Annotated[int, Ge(ge=0)] = 0, ambiguous_required_field_count: Annotated[int, Ge(ge=0)] = 0, constrained_required_field_issue_count: Annotated[int, Ge(ge=0)] = 0, table_count: Annotated[int, Ge(ge=0)] = 0, table_cell_count: Annotated[int, Ge(ge=0)] = 0, empty_table_cell_count: Annotated[int, Ge(ge=0)] = 0, summary_evidence: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary) -> None
```

Complete explicit Local OCR quality report without recognized content.

### `LocalOcrQualitySummary` (class)

```python
LocalOcrQualitySummary(*, algorithm_version: Literal['local-ocr-quality-v1'] = 'local-ocr-quality-v1', policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], decision: document_sdk.core.local_ocr_quality.LocalOcrQualityDecision, evaluated_input_count: Annotated[int, Ge(ge=0)], passed_input_count: Annotated[int, Ge(ge=0)], failed_input_count: Annotated[int, Ge(ge=0)], evaluated_pages: tuple[int, ...] = (), evaluated_frames: tuple[int, ...] = (), issue_counts_by_code: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCount, ...], MaxLen(max_length=8)] = (), reason_codes: Annotated[tuple[document_sdk.core.local_ocr_quality.LocalOcrQualityIssueCode, ...], MaxLen(max_length=8)] = (), failed_pages: tuple[int, ...] = (), failed_frames: tuple[int, ...] = (), retry_recommended: bool = False, recommended_retry_pages: tuple[int, ...] = (), recommended_retry_frames: tuple[int, ...] = (), character_count: Annotated[int, Ge(ge=0)], region_count: Annotated[int, Ge(ge=0)], confidence_weighted_character_count: Annotated[int, Ge(ge=0)], low_confidence_character_count: Annotated[int, Ge(ge=0)], suspicious_character_count: Annotated[int, Ge(ge=0)], region_area_numerator: Annotated[int, Ge(ge=0)], region_area_denominator: Annotated[int, Ge(ge=0)], required_field_count: Annotated[int, Ge(ge=0)], missing_required_field_count: Annotated[int, Ge(ge=0)], ambiguous_required_field_count: Annotated[int, Ge(ge=0)], constrained_required_field_issue_count: Annotated[int, Ge(ge=0)], table_count: Annotated[int, Ge(ge=0)], table_cell_count: Annotated[int, Ge(ge=0)], empty_table_cell_count: Annotated[int, Ge(ge=0)]) -> None
```

Content-free durable projection suitable for manifests and Resume.

### `LocalOcrRawRegion` (class)

```python
LocalOcrRawRegion(*, text: Annotated[str, MaxLen(max_length=100000)], polygon: Annotated[tuple[PixelPoint, ...], MinLen(min_length=4), MaxLen(max_length=16)], confidence: Annotated[float, Ge(ge=0), Le(le=1)], reading_order: Annotated[int, Ge(ge=0)], language: SafeIdentity | None = None) -> None
```

One fully validated safe OCR region in pixel coordinates.

### `LocalOcrRawResult` (class)

```python
LocalOcrRawResult(*, regions: tuple[document_sdk.ocr.local_models.LocalOcrRawRegion, ...] = ()) -> None
```

Fully validated safe raw-object-free OCR result.

### `LocalOcrRuntimeCapability` (class)

```python
LocalOcrRuntimeCapability(*, engine_name: SafeCapabilityComponent, engine_version: SafeCapabilityComponent, model_id: SafeCapabilityComponent, language_profile: document_sdk.ocr.model_policy.LocalOcrLanguageProfile, languages: Annotated[tuple[SafeCapabilityComponent, ...], MinLen(min_length=1), MaxLen(max_length=8)], device_class: Literal['cpu'], execution_provider: Literal['CPUExecutionProvider'], dependency_versions: Annotated[tuple[tuple[SafeCapabilityComponent, SafeCapabilityComponent], ...], MinLen(min_length=1), MaxLen(max_length=32)], python_major: Annotated[int, Ge(ge=3), Le(le=99)], python_minor: Annotated[int, Ge(ge=0), Le(le=99)], platform_system: SafeCapabilityComponent, platform_machine: SafeCapabilityComponent, runtime_verification: Literal['declared', 'verified']) -> None
```

Content-safe declared or runtime-verified Local OCR capability.

### `LocalOcrStructuredQualityPolicy` (class)

```python
LocalOcrStructuredQualityPolicy(*, maximum_missing_required_fields: Annotated[int | None, Ge(ge=0)] = None, minimum_table_count: Annotated[int | None, Ge(ge=0)] = None, maximum_empty_table_cell_ratio: Annotated[float | None, Ge(ge=0), Le(le=1)] = None) -> None
```

Explicit Structured Extraction and table-completeness quality rules.

### `LocalOcrUnsupportedInputError` (exception)


Raised when content is not a supported PDF or image family.

### `LocalOcrUnsupportedLanguageError` (exception)


Raised before work when a Local OCR language profile is unsupported.

### `MockOcrProvider` (class)

```python
MockOcrProvider(*, context: 'ProviderContext', document: 'Document', warnings: 'tuple[ProcessingWarning, ...]' = (), errors: 'tuple[ProcessingError, ...]' = (), failure: 'Exception | None' = None) -> 'None'
```

Return injected normalized OCR data without network access.

```python
MockOcrProvider.analyze(self, path: 'Path', *, options: 'OcrAnalysisOptions | None' = None) -> 'ProcessingResult[Document]'
```
Return injected OCR data and safe provider metadata.

Args:
    path: Existing local regular file representing the explicit input.
    options: Optional provider-neutral analysis options. The deterministic
        mock accepts and ignores these options.

Returns:
    The injected document, warnings, errors, and safe provider identity.

Raises:
    FileAccessError: If the explicit input is not a regular file.
    CredentialResolutionError: If runtime credential resolution fails.
    DocumentProcessingError: If an injected provider failure occurs.

### `OcrAnalysisOptions` (class)

```python
OcrAnalysisOptions(*, pages: tuple[int, ...] | None = None, locale: str | None = None, features: tuple[document_sdk.ocr.models.DocumentAnalysisFeature, ...] = (), query_fields: tuple[str, ...] = ()) -> None
```

Optional selective pages and locale for an OCR analysis.

### `OcrProvider` (class)

```python
OcrProvider(*args, **kwargs)
```

Normalize an explicitly selected OCR implementation.

```python
OcrProvider.analyze(self, path: 'Path', *, options: 'OcrAnalysisOptions | None' = None) -> 'ProcessingResult[Document]'
```
Analyze one local file and return normalized SDK models.

### `RapidOcrEngine` (class)

```python
RapidOcrEngine(*, model_policy: 'LocalOcrModelSelectionPolicy | None' = None, config: 'RapidOcrEngineConfig | None' = None, model_set: 'RapidOcrModelSet | None' = None) -> 'None'
```

Pinned, lazy, CPU-only RapidOCR implementation of ``LocalOcrEngine``.

```python
RapidOcrEngine.recognize(self, image: 'LocalOcrImageInput') -> 'LocalOcrEngineResult'
```
Run one RGB in-memory inference and return canonical SDK regions.

### `RapidOcrEngineConfig` (class)

```python
RapidOcrEngineConfig(*, intra_op_num_threads: Annotated[int, Ge(ge=1), Le(le=16)] = 1, inter_op_num_threads: Annotated[int, Ge(ge=1), Le(le=16)] = 1, language_policy: tuple[typing.Literal['zh'], typing.Literal['en']] = ('zh', 'en'), preprocess_policy: Literal['sdk-rgb-to-rapidocr-bgr-v1'] = 'sdk-rgb-to-rapidocr-bgr-v1', output_canonicalization_version: Literal['rapidocr-output-v2'] = 'rapidocr-output-v2', text_score: Annotated[float, Ge(ge=0.0), Le(le=0.0)] = 0.0, max_candidates: Literal[1000] = 1000, max_output_regions: Annotated[int, Ge(ge=1), Le(le=1000)] = 1000, max_model_files: Literal[3] = 3, max_model_file_bytes: Annotated[int, Gt(gt=0), Le(le=64000000)] = 64000000, max_total_model_bytes: Annotated[int, Gt(gt=0), Le(le=128000000)] = 128000000) -> None
```

JSON-safe deterministic CPU inference policy.

### `RapidOcrEngineInitializationError` (exception)


Raised when the fixed CPU runtime cannot be initialized safely.

### `RapidOcrExecutionError` (exception)


Raised for inference failures or unsupported third-party output.

### `RapidOcrModelSet` (class)

```python
RapidOcrModelSet(*, model_id: ModelId, detection_model: pathlib.Path, classification_model: pathlib.Path, recognition_model: pathlib.Path, detection_sha256: Sha256, classification_sha256: Sha256, recognition_sha256: Sha256) -> None
```

Runtime-only paths for the single approved ONNX model manifest.

### `RapidOcrModelValidationError` (exception)


Raised when a local ONNX model set violates its declared identity.

### `apply_azure_page_fallback` (function)

```python
apply_azure_page_fallback(source: 'Path', *, local_document: 'Document', quality_report: 'LocalOcrQualityReport', preprocessing_report: 'LocalOcrPreprocessingReport | None' = None, policy: 'AzurePageFallbackPolicy', azure_provider: 'object', pdf_limits: 'PdfProcessingLimits | None' = None, image_limits: 'ImageProcessingLimits | None' = None, source_verifier: 'Callable[[], None] | None' = None) -> 'AzurePageFallbackResult'
```

Replace only quality-recommended inputs using a verified source Snapshot.

### `inspect_local_ocr_runtime_capability` (function)

```python
inspect_local_ocr_runtime_capability(*, model_policy: 'LocalOcrModelSelectionPolicy | None' = None, engine: 'object | None' = None) -> 'LocalOcrRuntimeCapability'
```

Return actual-platform capability without model paths or runtime objects.

### `local_ocr_preprocessing_policy_fingerprint` (function)

```python
local_ocr_preprocessing_policy_fingerprint(policy: 'LocalOcrPreprocessingPolicy') -> 'str'
```

Return the canonical path-free policy fingerprint.

## `document_sdk.pdf`


### `UNIFIED_PDF_HYBRID_RESULT_VERSION` (value)


str(object='') -> str

### `UNIFIED_PDF_RESULT_VERSION` (value)


str(object='') -> str

### `PdfAnalysisMode` (class)

```python
PdfAnalysisMode(*values)
```

Small public mode set; every advanced capability is opt-in.

### `PdfLimitExceededError` (exception)

```python
PdfLimitExceededError(*, limit_name: 'str', observed: 'float', maximum: 'float') -> 'None'
```

Raised before PDF processing would exceed a configured limit.

### `PdfProcessingLimits` (class)

```python
PdfProcessingLimits(*, max_file_bytes: Annotated[int, Gt(gt=0), Le(le=10000000000)] = 512000000, max_pages: Annotated[int, Gt(gt=0), Le(le=100000)] = 1000, max_page_width_points: Annotated[float, Gt(gt=0), Le(le=1000000)] = 10000, max_page_height_points: Annotated[float, Gt(gt=0), Le(le=1000000)] = 10000, max_page_area_points: Annotated[float, Gt(gt=0), Le(le=1000000000000)] = 50000000, max_native_text_pages: Annotated[int, Gt(gt=0), Le(le=100000)] = 1000, max_native_text_characters: Annotated[int, Gt(gt=0), Le(le=1000000000)] = 20000000, max_render_dpi: Annotated[int, Gt(gt=0), Le(le=2400)] = 300, max_render_width: Annotated[int, Gt(gt=0), Le(le=1000000)] = 20000, max_render_height: Annotated[int, Gt(gt=0), Le(le=1000000)] = 20000, max_render_pixels: Annotated[int, Gt(gt=0), Le(le=1000000000000)] = 25000000, max_output_bytes: Annotated[int, Gt(gt=0), Le(le=10000000000)] = 20000000) -> None
```

Explicit bounds for local PDF inspection, text, and rendering.

### `PdfRenderLimitExceededError` (exception)

```python
PdfRenderLimitExceededError(*, limit_name: 'str', observed: 'float', maximum: 'float') -> 'None'
```

Raised before PDF rendering or encoding exceeds a configured limit.

### `UnifiedPdfAnalysisOptions` (class)

```python
UnifiedPdfAnalysisOptions(*, mode: document_sdk.pdf.unified.PdfAnalysisMode = <PdfAnalysisMode.STANDARD: 'STANDARD'>, limits: document_sdk.pdf.models.PdfProcessingLimits = <factory>) -> None
```

Aggregate public options without exposing private pipeline flags.

### `UnifiedPdfHybridCapabilityOutcome` (class)

```python
UnifiedPdfHybridCapabilityOutcome(*, page_number: Annotated[int, Ge(ge=1), Le(le=2000)], capability: Literal['OCR_TEXT', 'LAYOUT', 'TABLES'], state: Literal['FULFILLED', 'PARTIAL', 'NOT_APPLIED', 'UNAVAILABLE', 'CONFLICT'], reason_codes: Annotated[tuple[str, ...], MaxLen(max_length=32)] = ()) -> None
```

Stable content-safe projection of one effective Hybrid capability.

### `UnifiedPdfHybridResult` (class)

```python
UnifiedPdfHybridResult(*, schema_version: Literal['document_sdk.pdf.unified_hybrid_result.v2'] = 'document_sdk.pdf.unified_hybrid_result.v2', document_id: Annotated[str, _PydanticGeneralMetadata(pattern='^P3CE1-document-[0-9a-f]{64}$')], source_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], status: Literal['COMPLETED'], availability: Literal['AVAILABLE', 'PARTIAL', 'UNAVAILABLE'], page_count: Annotated[int, Ge(ge=0)], pages: tuple[document_sdk.pdf.unified.UnifiedPdfPage, ...], text: str, tables: tuple[document_sdk.pdf.unified.UnifiedPdfTable, ...], document_table_count: Annotated[int, Ge(ge=0)], transition_count: Annotated[int, Ge(ge=0)], warnings: tuple[str, ...] = (), limitations: tuple[str, ...] = (), provenance: document_sdk.pdf.unified._UnifiedPdfProvenance, family: NoneType = None, family_status: Literal['REVIEW_REQUIRED'] = 'REVIEW_REQUIRED', family_auto_assignment: bool = False, processing_mode: Literal[<PdfAnalysisMode.ADVANCED_HYBRID: 'ADVANCED_HYBRID'>] = <PdfAnalysisMode.ADVANCED_HYBRID: 'ADVANCED_HYBRID'>, hybrid: document_sdk.pdf.unified.UnifiedPdfHybridSummary) -> None
```

Unified structural result with a bounded Hybrid execution summary.

### `UnifiedPdfHybridSummary` (class)

```python
UnifiedPdfHybridSummary(*, cloud_status: Literal['NOT_REQUESTED', 'NOT_EXECUTED_DISABLED', 'NOT_EXECUTED_PROVIDER_UNAVAILABLE', 'NOT_EXECUTED_LIMIT', 'COMPLETED', 'COMPLETED_PARTIAL', 'FAILED_CONTROLLED'], submission_status: Literal['NOT_SUBMITTED', 'SUBMITTED', 'UNKNOWN'], submission_payload_scope: Literal['NOT_APPLICABLE', 'FULL_DOCUMENT_BYTES'], analysis_selection_scope: Literal['NOT_APPLICABLE', 'SELECTED_PAGES'], provider_name: Literal['azure-document-intelligence'] = 'azure-document-intelligence', model_id: Optional[Literal['prebuilt-layout']] = None, api_version: Optional[Literal['2024-11-30']] = None, requested_page_numbers: Annotated[tuple[int, ...], MaxLen(max_length=2000)] = (), returned_page_numbers: Annotated[tuple[int, ...], MaxLen(max_length=2000)] = (), applied_page_numbers: Annotated[tuple[int, ...], MaxLen(max_length=2000)] = (), effective_capability_outcomes: Annotated[tuple[document_sdk.pdf.unified.UnifiedPdfHybridCapabilityOutcome, ...], MaxLen(max_length=6000)] = (), local_preserved_text_count: Annotated[int, Ge(ge=0), Le(le=2000000)], cloud_filled_text_count: Annotated[int, Ge(ge=0), Le(le=2000000)], local_preserved_table_count: Annotated[int, Ge(ge=0), Le(le=2000000)], cloud_filled_table_count: Annotated[int, Ge(ge=0), Le(le=2000000)], conflict_count: Annotated[int, Ge(ge=0), Le(le=2000000)], continuity_unavailable_count: Annotated[int, Ge(ge=0), Le(le=2000000)], review_required: bool, deletion_status: Literal['NOT_REQUESTED', 'SUCCEEDED', 'FAILED', 'UNAVAILABLE'], failure_category: Optional[Literal['CLOUD_PROVIDER_UNAVAILABLE', 'CLOUD_CONFIGURATION_ERROR', 'CLOUD_REQUEST_LIMIT', 'CLOUD_PROVIDER_TIMEOUT', 'CLOUD_PROVIDER_REJECTED', 'CLOUD_RESPONSE_INVALID', 'CLOUD_RESULT_LIMIT_EXCEEDED', 'CLOUD_DELETE_FAILED', 'CLOUD_ANALYSIS_FAILED']] = None, warnings: Annotated[tuple[str, ...], MaxLen(max_length=512)] = (), limitations: Annotated[tuple[str, ...], MaxLen(max_length=512)] = ()) -> None
```

Bounded public operational summary for private Canonical Hybrid analysis.

### `UnifiedPdfPage` (class)

```python
UnifiedPdfPage(*, page_number: Annotated[int, Ge(ge=1)], width_points: Annotated[float, Gt(gt=0)], height_points: Annotated[float, Gt(gt=0)], rotation: Literal[0, 90, 180, 270], text: str, table_ids: tuple[str, ...] = (), availability: Literal['AVAILABLE', 'PARTIAL', 'UNAVAILABLE', 'UNSUPPORTED', 'LIMITED_EVIDENCE'], limitations: tuple[str, ...] = ()) -> None
```

Stable public page projection.

### `UnifiedPdfResult` (class)

```python
UnifiedPdfResult(*, schema_version: Literal['document_sdk.pdf.unified_result.v2'] = 'document_sdk.pdf.unified_result.v2', document_id: Annotated[str, _PydanticGeneralMetadata(pattern='^P3CE1-document-[0-9a-f]{64}$')], source_sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], status: Literal['COMPLETED'], availability: Literal['AVAILABLE', 'PARTIAL', 'UNAVAILABLE'], page_count: Annotated[int, Ge(ge=0)], pages: tuple[document_sdk.pdf.unified.UnifiedPdfPage, ...], text: str, tables: tuple[document_sdk.pdf.unified.UnifiedPdfTable, ...], document_table_count: Annotated[int, Ge(ge=0)], transition_count: Annotated[int, Ge(ge=0)], warnings: tuple[str, ...] = (), limitations: tuple[str, ...] = (), provenance: document_sdk.pdf.unified._UnifiedPdfProvenance, family: NoneType = None, family_status: Literal['REVIEW_REQUIRED'] = 'REVIEW_REQUIRED', family_auto_assignment: bool = False, processing_mode: document_sdk.pdf.unified.PdfAnalysisMode) -> None
```

Stable public projection of private Canonical evidence.

### `UnifiedPdfTable` (class)

```python
UnifiedPdfTable(*, table_id: Annotated[str, _PydanticGeneralMetadata(pattern='^P3CE1-table-[0-9a-f]{64}$')], page_number: Annotated[int, Ge(ge=1)], row_count: Annotated[int, Ge(ge=1)], column_count: Annotated[int, Ge(ge=1)], cells: tuple[document_sdk.pdf.unified.UnifiedPdfTableCell, ...], document_table_ids: tuple[str, ...] = (), availability: Literal['AVAILABLE', 'PARTIAL', 'UNAVAILABLE', 'UNSUPPORTED', 'LIMITED_EVIDENCE'], limitations: tuple[str, ...] = ()) -> None
```

Stable public page-table projection.

### `UnifiedPdfTableCell` (class)

```python
UnifiedPdfTableCell(*, row_index: Annotated[int, Ge(ge=0)], column_index: Annotated[int, Ge(ge=0)], row_span: Annotated[int, Ge(ge=1)], column_span: Annotated[int, Ge(ge=1)], text: str | None, availability: Literal['AVAILABLE', 'PARTIAL', 'UNAVAILABLE', 'UNSUPPORTED', 'LIMITED_EVIDENCE']) -> None
```

Stable public table-cell projection.

### `analyze_pdf` (function)

```python
analyze_pdf(source: 'bytes | bytearray | memoryview | str | PathLike[str]', *, options: 'UnifiedPdfAnalysisOptions | None' = None, hybrid_provider: 'AzureDocumentIntelligenceProvider | None' = None) -> 'UnifiedPdfResult'
```

Analyze a PDF through one explicit advanced public mode.

### `extract_native_text` (function)

```python
extract_native_text(path: 'Path', *, limits: 'PdfProcessingLimits | None' = None) -> 'Document'
```

Extract PDFium native text into traceable SDK document models.

Args:
    path: Local PDF path.
    limits: Optional explicit PDF resource limits.

Returns:
    A normalized document with one text block per non-empty page.

### `inspect_pdf` (function)

```python
inspect_pdf(path: 'Path', *, limits: 'PdfProcessingLimits | None' = None) -> 'PdfInspection'
```

Inspect pages, dimensions, rotation, and native text availability.

Args:
    path: Local PDF path.
    limits: Optional explicit PDF resource limits.

Returns:
    SDK-owned PDF inspection data.

### `render_page` (function)

```python
render_page(path: 'Path', page_number: 'int', *, dpi: 'int' = 144, limits: 'PdfProcessingLimits | None' = None) -> 'RenderedPage'
```

Render one one-based PDF page to PNG bytes.

Args:
    path: Local PDF path.
    page_number: Public one-based page number.
    dpi: Positive output resolution.
    limits: Optional explicit PDF resource limits.

Returns:
    An SDK-owned encoded rendered page.

### `render_region` (function)

```python
render_region(path: 'Path', page_number: 'int', bounding_box: 'BoundingBox', *, dpi: 'int' = 144, limits: 'PdfProcessingLimits | None' = None) -> 'RenderedPage'
```

Render a normalized top-left-origin PDF page region to PNG bytes.

Args:
    path: Local PDF path.
    page_number: Public one-based page number.
    bounding_box: Normalized region in rendered-page coordinates.
    dpi: Positive output resolution.
    limits: Optional explicit PDF resource limits.

Returns:
    An SDK-owned encoded region image.

## `document_sdk.pipeline`


### `HybridPdfAnalysisOptions` (class)

```python
HybridPdfAnalysisOptions(*, locale: str | None = None, features: tuple[document_sdk.ocr.models.DocumentAnalysisFeature, ...] = ()) -> None
```

Provider-neutral options for local-first hybrid PDF analysis.

### `OcrProviderRequiredError` (exception)


Raised when OCR-candidate PDF pages require an explicit Provider.

### `analyze_pdf_hybrid` (function)

```python
analyze_pdf_hybrid(path: 'Path', *, ocr_provider: 'OcrProvider | None' = None, options: 'HybridPdfAnalysisOptions | None' = None, limits: 'PdfProcessingLimits | None' = None) -> 'ProcessingResult[Document]'
```

Combine local native text with explicit OCR for heuristic candidate pages.

## `document_sdk.providers`


### `CloudCancellationStatus` (class)

```python
CloudCancellationStatus(*values)
```

Best-effort cancellation outcome without implying billing reversal.

### `CloudExecutionAttemptEvidence` (class)

```python
CloudExecutionAttemptEvidence(*, evidence_version: Literal['cloud-execution-attempt-v3'], provider_name: NonEmptyString, profile_id: NonEmptyString, model_id: NonEmptyString | None = None, api_version: NonEmptyString | None = None, provider_resource_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], policy_fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], status: document_sdk.core.models.CloudExecutionAttemptStatus, logical_operation_count: Annotated[int, Strict(strict=True), Ge(ge=1), Le(le=1)] = 1, submitted_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1)] = 0, paid_or_possibly_paid_operation_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1)] = 0, transport_retry_count: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=0)] = 0, requested_entire_input: bool, requested_pages: tuple[int, ...] = (), requested_frames: tuple[int, ...] = (), submitted_pages: tuple[int, ...] = (), submitted_frames: tuple[int, ...] = (), input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=2000000000)] = 0, cancellation_status: document_sdk.core.models.CloudCancellationStatus = <CloudCancellationStatus.NOT_ATTEMPTED: 'not_attempted'>) -> None
```

Content-free evidence for one attempted cloud execution boundary.

### `CloudExecutionAttemptStatus` (class)

```python
CloudExecutionAttemptStatus(*values)
```

Content-safe lifecycle state for one logical cloud operation.

### `CloudExecutionPolicy` (class)

```python
CloudExecutionPolicy(*, allow_cloud_execution: bool = False, allow_cloud_fallback: bool = False, max_logical_cloud_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_submitted_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_paid_or_possibly_paid_operations: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_pages_or_frames: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=1000000)] = 0, max_input_bytes: Annotated[int, Strict(strict=True), Ge(ge=0), Le(le=2000000000)] = 0, allow_retry_possibly_paid: bool = False, policy_version: Literal['cloud-execution-policy-v2'] = 'cloud-execution-policy-v2') -> None
```

Provider-neutral, explicitly authorized finite cloud execution policy.

### `CredentialResolver` (class)

```python
CredentialResolver(*args, **kwargs)
```

Resolve an opaque credential object at operation time.

```python
CredentialResolver.resolve(self) -> 'object'
```
Return an opaque runtime credential object.

### `MockCredentialResolver` (class)

```python
MockCredentialResolver(credential: 'object', *, error: 'Exception | None' = None) -> 'None'
```

A redacting credential resolver for tests and examples.

```python
MockCredentialResolver.resolve(self) -> 'object'
```
Return the injected credential or raise a redacted SDK error.

### `ProviderConfig` (class)

```python
ProviderConfig(*, provider_name: NonEmptyString, profile_id: NonEmptyString, endpoint: pydantic.networks.HttpUrl | None = None, region: NonEmptyString | None = None, model_id: NonEmptyString | None = None, deployment_name: NonEmptyString | None = None, processor_id: NonEmptyString | None = None, timeout_seconds: Annotated[float, Gt(gt=0), Le(le=600)] = 30, retry: document_sdk.providers.config.RetryConfig = <factory>) -> None
```

Strict provider settings that can never contain credentials.

### `ProviderContext` (class)

```python
ProviderContext(*, profile_id: 'str', config: '_ProviderConfiguration', credential_resolver: 'CredentialResolver', metadata: 'ProviderMetadata | None' = None) -> 'None'
```

Bind one profile's safe configuration and runtime resolver.

```python
ProviderContext.safe_dict(self) -> 'dict[str, object]'
```
Return JSON-compatible context data without the resolver.

### `ProviderMetadata` (class)

```python
ProviderMetadata(*, provider_name: NonEmptyString, profile_id: NonEmptyString, model_id: NonEmptyString | None = None, attributes: collections.abc.Mapping[str, JsonValue] = <factory>) -> None
```

Serializable provider facts known to be non-secret.

### `RetryConfig` (class)

```python
RetryConfig(*, max_attempts: Annotated[int, Ge(ge=1), Le(le=10)] = 3, base_delay_seconds: Annotated[float, Ge(ge=0), Le(le=60)] = 0.25, max_delay_seconds: Annotated[float, Ge(ge=0), Le(le=300)] = 5) -> None
```

Non-secret retry behavior for a provider instance.

## `document_sdk.workflow`


### `WORKFLOW_ARTIFACT_SERIALIZATION_VERSION` (value)


str(object='') -> str

### `WORKFLOW_CONTRACT_VERSION` (value)


str(object='') -> str

### `WORKFLOW_MANIFEST_VERSION` (value)


str(object='') -> str

### `DocumentWorkflowArtifactError` (exception)


Raised when a caller-owned artifact cannot be trusted or accessed.

### `DocumentWorkflowConfigurationError` (exception)


Raised when a workflow request or Provider bundle is inconsistent.

### `DocumentWorkflowError` (exception)


Base class for expected one-file workflow failures.

### `DocumentWorkflowIntakeIssue` (class)

```python
DocumentWorkflowIntakeIssue(*, code: Annotated[str, _PydanticGeneralMetadata(pattern='^[a-z][a-z0-9_]{0,127}$')], category: document_sdk.workflow.models.WorkflowIssueCategory, message: Annotated[str, MinLen(min_length=1), MaxLen(max_length=256), _PydanticGeneralMetadata(pattern="^[A-Za-z0-9][A-Za-z0-9 .,'()_-]{0,255}$")], retryable: bool, count: Annotated[int | None, Ge(ge=1)] = None, source: SourceReference | None = None) -> None
```

One bounded, stage-less issue emitted before a Workflow Plan exists.

### `DocumentWorkflowIntakeResult` (class)

```python
DocumentWorkflowIntakeResult(*, contract_version: Literal['2'] = '2', sdk_version: Annotated[str, MinLen(min_length=1), MaxLen(max_length=256)] = '1.8.0', status: document_sdk.workflow.models.DocumentWorkflowIntakeStatus, source: document_sdk.workflow.models.WorkflowSourceIdentity | None = None, detected_document_type: document_sdk.document.models.DocumentType | None = None, detected_document_format: document_sdk.document.models.DocumentFormat | None = None, workflow_result: document_sdk.workflow.models.DocumentWorkflowResult | None = None, issues: tuple[document_sdk.workflow.models.DocumentWorkflowIntakeIssue, ...] = ()) -> None
```

Minimal outer contract for one planned or pre-Plan file outcome.

### `DocumentWorkflowIntakeStatus` (class)

```python
DocumentWorkflowIntakeStatus(*values)
```

Stable outer outcome for one universal one-file intake invocation.

### `DocumentWorkflowManifest` (class)

```python
DocumentWorkflowManifest(*, manifest_version: Literal['2'] = '2', contract_version: Literal['2'] = '2', sdk_version: Annotated[str, MinLen(min_length=1), MaxLen(max_length=256)], source: document_sdk.workflow.models.WorkflowSourceIdentity, tenant_scope_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], document_type: document_sdk.document.models.DocumentType, document_format: document_sdk.document.models.DocumentFormat, request_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], plan_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], workflow_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], stages: tuple[document_sdk.workflow.models.WorkflowStageResult, ...], usage: document_sdk.workflow.models.WorkflowUsage, artifact_references: tuple[document_sdk.workflow.models.WorkflowArtifactReference, ...] = (), warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = (), issues: tuple[document_sdk.workflow.models.WorkflowStageIssue, ...] = (), limitations: tuple[document_sdk.workflow.models.WorkflowLimitation, ...] = (), limitation_codes: tuple[str, ...] = (), local_ocr_quality_summary: document_sdk.core.local_ocr_quality.LocalOcrQualitySummary | None = None, local_ocr_quality_owner_stage: document_sdk.workflow.models.WorkflowStageKind | None = None, local_ocr_quality_binding: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None) -> None
```

Content-free stage-aware Resume evidence for one exact source.

### `DocumentWorkflowOutputPolicy` (class)

```python
DocumentWorkflowOutputPolicy(*, include_native_result: bool = True, include_top_level_document: bool = True, include_structured_extraction: bool = True, persist_intermediate_artifacts: bool = False, max_artifact_bytes: Annotated[int, Ge(ge=1), Le(le=500000000)] = 67108864, excel_mode: document_sdk.workflow.models.ExcelWorkflowOutputMode = <ExcelWorkflowOutputMode.INSPECTION: 'inspection'>, excel_ranges: tuple[document_sdk.workflow.models.WorkflowExcelRangeSelection, ...] = (), max_excel_cells: Annotated[int, Ge(ge=1), Le(le=1000000)] = 100000, include_excel_feature_inventory: bool = False) -> None
```

Bound content-bearing result fields and intermediate artifact bytes.

### `DocumentWorkflowPlan` (class)

```python
DocumentWorkflowPlan(*, contract_version: Literal['2'] = '2', source: document_sdk.workflow.models.WorkflowSourceIdentity, document_type: document_sdk.document.models.DocumentType, document_format: document_sdk.document.models.DocumentFormat, route: document_sdk.workflow.models.WorkflowRoute, pdf_processing_mode: document_sdk.workflow.models.WorkflowPdfProcessingMode = <WorkflowPdfProcessingMode.COMPATIBILITY: 'compatibility'>, pdf_preflight: document_sdk.workflow.models.WorkflowPdfPreflight | None = None, ocr_scope: document_sdk.workflow.models.WorkflowOcrScope, ocr_requested: bool, azure_permitted: bool, azure_required: bool, extraction_mode: document_sdk.workflow.models.WorkflowExtractionMode, request_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], plan_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], workflow_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], provider_requirements: tuple[document_sdk.workflow.models.WorkflowProviderRequirement, ...] = (), provider_identities: tuple[document_sdk.workflow.models.WorkflowProviderIdentity, ...] = (), required_artifacts: tuple[document_sdk.workflow.models.WorkflowArtifactKind, ...] = (), stages: tuple[document_sdk.workflow.models.WorkflowStagePlan, ...], supported: bool = True, limitations: tuple[document_sdk.workflow.models.WorkflowLimitation, ...] = ()) -> None
```

Provider-free, content-safe plan built before credential resolution.

### `DocumentWorkflowPolicy` (class)

```python
DocumentWorkflowPolicy(*, azure_execution_policy: document_sdk.core.models.CloudExecutionPolicy = <factory>, allow_local_recompute: bool = True) -> None
```

Explicit local recompute and independent cloud authorization policies.

### `DocumentWorkflowProviders` (class)

```python
DocumentWorkflowProviders(local_ocr: 'LocalOcrProvider | WorkflowLocalOcrProvider | None' = None, azure: 'AzureDocumentIntelligenceProvider | None' = None) -> None
```

Runtime-only explicit Providers; unused fields are never inspected.

### `DocumentWorkflowRequest` (class)

```python
DocumentWorkflowRequest(*, tenant_scope_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], analysis_options: document_sdk.document.models.DocumentAnalysisOptions = <factory>, hybrid_pdf_options: document_sdk.pipeline.models.HybridPdfAnalysisOptions | None = None, pdf_processing_mode: document_sdk.workflow.models.WorkflowPdfProcessingMode = <WorkflowPdfProcessingMode.COMPATIBILITY: 'compatibility'>, ocr_route: document_sdk.workflow.models.WorkflowOcrRoute = <WorkflowOcrRoute.NONE: 'none'>, extraction_mode: document_sdk.workflow.models.WorkflowExtractionMode = <WorkflowExtractionMode.NONE: 'none'>, extraction_schema: document_sdk.extraction.models.ExtractionSchema | None = None, structured_extraction_options: document_sdk.extraction.models.StructuredExtractionOptions | None = None, policy: document_sdk.workflow.models.DocumentWorkflowPolicy = <factory>, output_policy: document_sdk.workflow.models.DocumentWorkflowOutputPolicy = <factory>) -> None
```

Content-bearing request for one explicit stage-aware workflow.

### `DocumentWorkflowResult` (class)

```python
DocumentWorkflowResult(*, contract_version: Literal['2'] = '2', status: document_sdk.workflow.models.DocumentWorkflowStatus, source: document_sdk.workflow.models.WorkflowSourceIdentity, detected_document_type: document_sdk.document.models.DocumentType, detected_document_format: document_sdk.document.models.DocumentFormat, plan: document_sdk.workflow.models.DocumentWorkflowPlan, stage_results: tuple[document_sdk.workflow.models.WorkflowStageResult, ...], native_result: Optional[Annotated[document_sdk.workflow.models.WorkflowPdfNativeResult | document_sdk.workflow.models.WorkflowExcelNativeResult | document_sdk.workflow.models.WorkflowImageNativeResult | document_sdk.workflow.models.WorkflowDocxNativeResult, FieldInfo(annotation=NoneType, required=True, discriminator='kind')]] = None, document: document_sdk.core.models.Document | None = None, structured_extraction: document_sdk.extraction.models.StructuredExtractionResult | None = None, usage: document_sdk.workflow.models.WorkflowUsage, warnings: tuple[document_sdk.core.results.ProcessingWarning, ...] = (), issues: tuple[document_sdk.workflow.models.WorkflowStageIssue, ...] = (), limitations: tuple[document_sdk.workflow.models.WorkflowLimitation, ...] = (), output_evidence: document_sdk.workflow.models.WorkflowOutputEvidence, manifest: document_sdk.workflow.models.DocumentWorkflowManifest, artifact_references: tuple[document_sdk.workflow.models.WorkflowArtifactReference, ...] = ()) -> None
```

Stable content-bearing Option-B envelope for every supported family.

### `DocumentWorkflowResultValidationError` (exception)


Raised when public workflow evidence is inconsistent.

### `DocumentWorkflowResumeError` (exception)


Raised when prior stage evidence cannot be resumed safely.

### `DocumentWorkflowStatus` (class)

```python
DocumentWorkflowStatus(*values)
```

Final state of one workflow invocation.

### `ExcelWorkflowOutputMode` (class)

```python
ExcelWorkflowOutputMode(*values)
```

Bounded Excel detail included in the workflow's native result.

### `WorkflowArtifactKind` (class)

```python
WorkflowArtifactKind(*values)
```

Content-bearing model stored behind an opaque caller-owned key.

### `WorkflowArtifactReference` (class)

```python
WorkflowArtifactReference(*, artifact_id: Annotated[str, _PydanticGeneralMetadata(pattern='^wf-artifact-v1-[0-9a-f]{64}$')], kind: document_sdk.workflow.models.WorkflowArtifactKind, media_type: Literal['application/vnd.document-sdk.workflow+json'] = 'application/vnd.document-sdk.workflow+json', serialization_version: Literal['2'] = '2', sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], byte_count: Annotated[int, Ge(ge=1), Le(le=500000000)], source: document_sdk.workflow.models.WorkflowSourceIdentity, tenant_scope_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], stage_kind: document_sdk.workflow.models.WorkflowStageKind, stage_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], output_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], route_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], model_name: Literal['Document', 'WorkflowNativeResult', 'StructuredExtractionResult']) -> None
```

Content-free reference to one caller-owned serialized model artifact.

### `WorkflowArtifactStore` (class)

```python
WorkflowArtifactStore(*args, **kwargs)
```

Store and load bounded bytes under an opaque SDK-generated identifier.

```python
WorkflowArtifactStore.store(self, artifact_id: 'str', payload: 'bytes') -> 'None'
```
Persist exact bytes under artifact_id without interpreting content.

```python
WorkflowArtifactStore.load(self, artifact_id: 'str') -> 'bytes'
```
Return the exact bytes previously stored under artifact_id.

### `WorkflowDocxNativeResult` (class)

```python
WorkflowDocxNativeResult(*, kind: Literal['word'] = 'word', analysis: document_sdk.document.models.DocxDocumentAnalysis) -> None
```

Exact existing DOCX analysis at the workflow native boundary.

### `WorkflowExcelNativeResult` (class)

```python
WorkflowExcelNativeResult(*, kind: Literal['excel'] = 'excel', analysis: document_sdk.document.models.ExcelDocumentAnalysis, ranges: tuple[document_sdk.workflow.models.WorkflowExcelRangeData, ...] = (), feature_inventory: document_sdk.excel.models.WorkbookFeatureInventory | None = None, detail_complete: bool = False) -> None
```

Existing Excel inspection plus explicitly bounded existing native details.

### `WorkflowExcelRangeData` (class)

```python
WorkflowExcelRangeData(*, selection: document_sdk.workflow.models.WorkflowExcelRangeSelection, data: document_sdk.core.models.WorksheetData) -> None
```

One exact requested Excel range and its existing native SDK result.

### `WorkflowExcelRangeSelection` (class)

```python
WorkflowExcelRangeSelection(*, sheet_name: Annotated[str, MinLen(min_length=1), MaxLen(max_length=31)], cell_range: Annotated[str, MinLen(min_length=1), MaxLen(max_length=64)]) -> None
```

One caller-bounded Excel range requested for native output.

### `WorkflowExtractionMode` (class)

```python
WorkflowExtractionMode(*values)
```

Optional extraction stage performed after Document normalization.

### `WorkflowImageNativeResult` (class)

```python
WorkflowImageNativeResult(*, kind: Literal['image'] = 'image', analysis: document_sdk.document.models.ImageDocumentAnalysis) -> None
```

Exact existing image/TIFF analysis at the workflow native boundary.

### `WorkflowIssueCategory` (class)

```python
WorkflowIssueCategory(*values)
```

Bounded, content-safe failure and warning categories.

### `WorkflowLimitation` (class)

```python
WorkflowLimitation(*, code: Annotated[str, _PydanticGeneralMetadata(pattern='^[a-z][a-z0-9_]{0,127}$')], message: Annotated[str, MinLen(min_length=1), MaxLen(max_length=256)]) -> None
```

Stable content-safe limitation evidence.

### `WorkflowLocalOcrProvider` (class)

```python
WorkflowLocalOcrProvider(provider: 'OcrProvider') -> None
```

Explicitly declare one caller-supplied OCR Provider as local-only.

### `WorkflowNativeResult` (value)


Runtime representation of an annotated type.

### `WorkflowOcrRoute` (class)

```python
WorkflowOcrRoute(*values)
```

Explicit OCR selection; no value performs Provider discovery.

### `WorkflowOcrScope` (class)

```python
WorkflowOcrScope(*values)
```

Observed OCR-candidate coverage without asserting physical page type.

### `WorkflowOutputEvidence` (class)

```python
WorkflowOutputEvidence(*, native_result_included: bool, top_level_document_included: bool, structured_extraction_included: bool, document_content_present: bool, excel_mode: document_sdk.workflow.models.ExcelWorkflowOutputMode | None = None, excel_cell_count: Annotated[int, Ge(ge=0)] = 0, truncated: bool = False, omitted_outputs: tuple[document_sdk.workflow.models.WorkflowArtifactKind, ...] = (), limitation_codes: tuple[str, ...] = ()) -> None
```

Content-free projection of included and deliberately omitted output.

### `WorkflowPdfNativeResult` (class)

```python
WorkflowPdfNativeResult(*, kind: Literal['pdf'] = 'pdf', analysis: document_sdk.document.models.PdfDocumentAnalysis) -> None
```

Exact existing PDF analysis at the workflow native boundary.

### `WorkflowPdfPreflight` (class)

```python
WorkflowPdfPreflight(*, page_count: Annotated[int, Ge(ge=1), Le(le=100000)], max_pages: Annotated[int, Ge(ge=1), Le(le=100000)], max_input_bytes: Annotated[int, Ge(ge=1), Le(le=2000000000)], original_whole_document: Literal[True] = True, native_text_extracted: Literal[False] = False) -> None
```

Content-free structural facts for one Azure-first PDF plan.

### `WorkflowPdfProcessingMode` (class)

```python
WorkflowPdfProcessingMode(*values)
```

Explicit PDF workflow behavior with the v1.3 route kept as default.

### `WorkflowProviderCategory` (class)

```python
WorkflowProviderCategory(*values)
```

Provider category required by a planned stage.

### `WorkflowProviderIdentity` (class)

```python
WorkflowProviderIdentity(*, category: document_sdk.workflow.models.WorkflowProviderCategory, fingerprint: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')]) -> None
```

Irreversible runtime Provider identity bound before credential access.

### `WorkflowProviderRequirement` (class)

```python
WorkflowProviderRequirement(*, category: document_sdk.workflow.models.WorkflowProviderCategory, stage_kind: document_sdk.workflow.models.WorkflowStageKind, required: Literal[True] = True) -> None
```

Content-free declaration of one explicit runtime dependency.

### `WorkflowRoute` (class)

```python
WorkflowRoute(*values)
```

Content-safe route selected from source facts and explicit request policy.

### `WorkflowSourceIdentity` (class)

```python
WorkflowSourceIdentity(*, sha256: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], byte_size: Annotated[int, Ge(ge=0), Le(le=2000000000)], file_descriptor_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')]) -> None
```

Path-free identity for exact bytes and their safe file descriptor.

### `WorkflowStageIssue` (class)

```python
WorkflowStageIssue(*, code: Annotated[str, _PydanticGeneralMetadata(pattern='^[a-z][a-z0-9_]{0,127}$')], category: document_sdk.workflow.models.WorkflowIssueCategory, message: Annotated[str, MinLen(min_length=1), MaxLen(max_length=256)], retryable: bool, count: Annotated[int | None, Ge(ge=1)] = None, stage_kind: document_sdk.workflow.models.WorkflowStageKind, provider_category: document_sdk.workflow.models.WorkflowProviderCategory | None = None, source: SourceReference | None = None) -> None
```

Sanitized issue for one exact workflow stage.

### `WorkflowStageKind` (class)

```python
WorkflowStageKind(*values)
```

Ordered, bounded one-file workflow stages.

### `WorkflowStagePlan` (class)

```python
WorkflowStagePlan(*, kind: document_sdk.workflow.models.WorkflowStageKind, status: Literal[<WorkflowStageStatus.PLANNED: 'planned'>, <WorkflowStageStatus.SKIPPED: 'skipped'>], stage_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], provider_category: document_sdk.workflow.models.WorkflowProviderCategory | None = None, cloud_authorization_required: bool = False, artifact_outputs: tuple[document_sdk.workflow.models.WorkflowArtifactKind, ...] = (), reason_code: Annotated[str | None, _PydanticGeneralMetadata(pattern='^[a-z][a-z0-9_]{0,127}$')] = None) -> None
```

One content-free planned stage.

### `WorkflowStageResult` (class)

```python
WorkflowStageResult(*, kind: document_sdk.workflow.models.WorkflowStageKind, status: Literal[<WorkflowStageStatus.SUCCEEDED: 'succeeded'>, <WorkflowStageStatus.FAILED: 'failed'>, <WorkflowStageStatus.SKIPPED: 'skipped'>, <WorkflowStageStatus.REUSED: 'reused'>, <WorkflowStageStatus.REVIEW_REQUIRED: 'review_required'>], input_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], stage_identity: Annotated[str, _PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')], output_identity: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, provider_category: document_sdk.workflow.models.WorkflowProviderCategory | None = None, provider_identity: Optional[Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[_PydanticGeneralMetadata(pattern='^[0-9a-f]{64}$')])]] = None, current_provider_usage: tuple[document_sdk.core.models.ProviderUsage, ...] = (), retained_provider_usage: tuple[document_sdk.core.models.ProviderUsage, ...] = (), current_cloud_attempts: tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...] = (), retained_cloud_attempts: tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...] = (), artifact_references: tuple[document_sdk.workflow.models.WorkflowArtifactReference, ...] = (), issues: tuple[document_sdk.workflow.models.WorkflowStageIssue, ...] = (), retry_eligible: bool = False, reuse_eligible: bool = False) -> None
```

Content-free lifecycle and operation evidence for one stage.

### `WorkflowStageStatus` (class)

```python
WorkflowStageStatus(*values)
```

Lifecycle state for one planned stage.

### `WorkflowUsage` (class)

```python
WorkflowUsage(*, current_provider_usage: tuple[document_sdk.core.models.ProviderUsage, ...] = (), retained_provider_usage: tuple[document_sdk.core.models.ProviderUsage, ...] = (), current_cloud_attempts: tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...] = (), retained_cloud_attempts: tuple[document_sdk.core.models.CloudExecutionAttemptEvidence, ...] = (), totals: document_sdk.core.models.ProviderUsageTotals = <factory>, local_stage_operation_count: Annotated[int, Ge(ge=0)] = 0, reused_stage_count: Annotated[int, Ge(ge=0)] = 0) -> None
```

Exact current/retained Provider history and aggregate operation totals.

### `plan_document_workflow` (function)

```python
plan_document_workflow(source: 'Path', request: 'DocumentWorkflowRequest') -> 'DocumentWorkflowPlan'
```

Inspect one source and return a content-safe Provider-free workflow plan.

### `run_document_workflow` (function)

```python
run_document_workflow(source: 'str | Path', request: 'DocumentWorkflowRequest', *, providers: 'DocumentWorkflowProviders', artifact_store: 'WorkflowArtifactStore | None' = None, resume_manifest: 'DocumentWorkflowManifest | None' = None) -> 'DocumentWorkflowResult'
```

Run one explicit, stage-aware workflow without implicit Provider selection.

### `run_document_workflow_intake` (function)

```python
run_document_workflow_intake(source: 'str | Path', request: 'DocumentWorkflowRequest', *, providers: 'DocumentWorkflowProviders', artifact_store: 'WorkflowArtifactStore | None' = None, resume_manifest: 'DocumentWorkflowManifest | None' = None) -> 'DocumentWorkflowIntakeResult'
```

Return one stable outcome while preserving the existing Workflow contract.
