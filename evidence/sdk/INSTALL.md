# Installation

Distribution: `document-processing-sdk` version `1.8.0`. Import: `document_sdk`.
Python requirement: `>=3.12,<3.13` (Python 3.12 only). The SDK wheel is `py3-none-any`; native third-party dependencies have separate platform requirements.

From this bundle directory, inside your Web application's compatible virtual environment:

```bash
python -m pip install ./dist/document_processing_sdk-1.8.0-py3-none-any.whl
```

For PDF and Excel support, select the actual declared extras:

```bash
python -m pip install "./dist/document_processing_sdk-1.8.0-py3-none-any.whl[pdf,excel]"
```

These consumer installation commands can resolve dependencies from the consumer's configured package index. This delivery was built and smoke-tested offline. The SDK wheel does **not** contain its dependencies or OCR models. For a fully offline consumer environment, separately provision the exact compatible dependency wheels for that OS/CPU/Python and install with `--no-index --find-links <approved-wheelhouse>`. A `--no-deps` installation alone does not establish dependency completeness.

Base runtime dependencies: defusedxml>=0.7,<1, pydantic>=2.10,<3. The complete optional groups and wheel metadata are in `metadata/PACKAGE_METADATA.json`; test/dev dependencies are not runtime requirements. The legacy `all` extra does not include `ocr-rapidocr` or all of the specialized `pdf` stack; explicitly select required extras.

| Capability | Extra / service |
| --- | --- |
| Local DOCX structure and common models | Base package; no Office application or cloud service required. |
| Excel `.xlsx`/`.xlsm` | `excel` (openpyxl); no Excel desktop or cloud required; macros not executed. |
| Local PDF inspection/text/rendering/analysis | `pdf`; uses PDFium/Pillow and the pinned PDF parser stack. No OCR/cloud service is required for native processing. |
| Local raster images | `image`; Pillow. OpenCV operations additionally require `image-opencv`. |
| Explicit local OCR | `ocr-rapidocr` and externally provisioned local models/configuration. Model weights are not in this bundle; runtime model download is disabled. |
| Explicit Azure Document Intelligence | `azure-document-intelligence`, application-selected provider/endpoint/profile and runtime credential resolution. Credentials must not be stored in SDK configuration or this bundle. |

Base/PDF/Excel/DOCX/image operations need no API-key environment variables. There is no automatic cloud upload, and no current OpenAI/LLM provider extra. Azure is optional and selected explicitly; credentials/identity are application responsibilities. Nothing here installs or configures a cloud account.

PDFium, Pillow, OpenCV, NumPy, ONNX Runtime and other selected dependencies may include native binaries. Use dependency wheels compatible with the target system; if native wheels are unavailable, system libraries/compiler requirements must be assessed for that target. This task did not validate such source builds. Do not assume Linux/Windows compatibility has been tested merely because the SDK wheel is platform-neutral.

Verified environment: macOS arm64, Python 3.12.13. Linux, Windows and x86_64 were NOT_VERIFIED. Smoke installed this wheel into a separate target, imported every SDK module from that target, reused the existing environment's dependencies, and exercised a two-cell workbook plus one blank PDF page. No full SDK suite, OCR, cloud, Web app deployment or 100K corpus rerun was performed.

The configured sdist contains source, tests, examples, license and empty fixture placeholders; it contains no actual corpus/benchmark data or old evidence. The wheel contains only the SDK package, typing marker and distribution metadata/license. Proprietary/internal-use license applies; packaging does not change license or constitute public publishing.
