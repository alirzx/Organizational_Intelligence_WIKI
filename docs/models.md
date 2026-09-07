# Extraction V1 models and inference

## Runtime profile

All three real backends are CPU-configured by default and have a mock alternative. The model services are process-local singletons shared by the independent endpoints and `/extract`. Backend wrappers exist at process startup, but heavy framework objects are loaded lazily on the first prediction and then reused for every request in that process.

| Capability | Backend setting | Baseline model | Threshold | V1 output |
|---|---|---|---:|---|
| OCR/paragraphs | `paddle` | `PaddlePaddle/arabic_PP-OCRv5_mobile_rec` + `PP-OCRv5_server_det` | 0.45 | `paragraph` |
| Figure/table | `pp_doclayout` | `PaddlePaddle/PP-DocLayoutV3` | 0.45 | `figure`, `table` |
| Stamp/signature | `rfdetr` | `bluecopa/rf-detr-stamp-signature-detector` | 0.50 | `stamp`, `signature` |

Thresholds and devices are `WIKI_HAMI_*` settings. Each backend has an initialization lock and an inference lock. This avoids duplicate initialization and unsafe concurrent prediction on a shared model. It also means same-family calls across pages are serialized.

## OCR — PaddleOCR

Backend: `app/modules/ocr/paddle_backend.py`. Adapter/grouping: `app/modules/ocr/adapter.py` and `paragraph_grouper.py`.

The backend constructs `PaddleOCR` with:

- text detector `PP-OCRv5_server_det`;
- text recognizer `arabic_PP-OCRv5_mobile_rec` (the repository-qualified setting is reduced to its final name for PaddleOCR);
- device `cpu` by default;
- document orientation classification and document unwarping disabled, because shared preprocessing owns source geometry;
- text-line orientation enabled by default, which also loads `PP-LCNet_x1_0_textline_ori`.

The recognition model is the Persian/Arabic-first baseline and the Paddle pipeline remains capable of recognizing the languages supported by the chosen recognition model. This repository does not auto-detect or route between multiple recognizers.

Input is the shared processed RGB Pillow image converted to an RGB NumPy array. PaddleOCR owns its internal tensor conversion, resize, padding, and normalization. `model.predict()` returns result objects/dicts whose inner `res` payload is parsed from `rec_texts`, `rec_scores`, `rec_boxes`, and `rec_polys`/`dt_polys`. Blank/below-threshold lines are removed, geometry becomes `OCRLine`, and lines are sorted top-to-bottom then left-to-right.

Wiki Hami then groups lines geometrically into paragraphs; Paddle does not emit the final V1 paragraphs. Paragraph text, raw text, confidence, union geometry, line count/confidences, and both detector/recognizer IDs are passed to the canonical adapter. Source coordinate restoration happens after grouping. Provenance uses module `ocr`, backend `paddle`, and the recognition model ID; current OCR provenance has no model version.

Limitations: paragraph grouping is not semantic, reading order is a simple geometric sort, multi-column documents can be challenging, and no language routing/text correction occurs.

## Figure/table — PP-DocLayoutV3

Backend: `app/modules/figure_table/pp_doclayout_backend.py`. Adapter: `adapter.py`.

`LayoutDetection` is created with `PP-DocLayoutV3` and the configured device (`cpu` default). Input is the shared processed RGB image converted to NumPy. The backend calls `predict(input=rgb, batch_size=1)` and parses each returned `boxes` entry: `score`, `coordinate` (four-value XYXY), `label`, and optional `cls_id`. It filters below 0.45, creates a rectangular polygon, then passes results to the adapter.

The installed model's label list includes `chart`, `figure_title`, `footer_image`, `header_image`, `image`, and `table` among many text/formula/header/footer classes. Actual V1 mapping is controlled by code plus configuration:

- `table` maps to `table`; a future label starting with `table` also maps unless it contains `caption`.
- configured exact `figure,image,chart` labels map to `figure`;
- as a fallback, any label containing `figure`, `image`, or `chart` maps to `figure` unless it also contains `caption` or `title`.

With the current PP-DocLayoutV3 labels this means `chart`, `image`, `header_image`, and `footer_image` become `figure`; `table` becomes `table`; `figure_title` is excluded. Every other model label is ignored. Metadata retains the original label/class ID. Provenance uses module `figure_table`, backend `pp_doclayout`, and model ID `PaddlePaddle/PP-DocLayoutV3`; current model version is null.

Limitations: the adapter currently consumes four-value coordinates and represents them as rectangular polygons even though newer layout architectures can express richer geometry. It does not extract cells, rows, columns, captions, titles, or reading order.

## Stamp/signature — RF-DETR

Backend: `app/modules/stamp_signature/rfdetr_backend.py`. Adapter: `adapter.py`.

The baseline is the Apache-2.0 `bluecopa/rf-detr-stamp-signature-detector`, an RF-DETR Base detector with a DINOv2 backbone. Its published four classes and the checkpoint-specific mapping implemented here are:

| Class ID | Model label | V1 behavior |
|---:|---|---|
| 0 | `stamp` | expose as `stamp` |
| 1 | `signature` | expose as `signature` |
| 2 | `checkbox_checked` | ignore |
| 3 | `checkbox_unchecked` | ignore |

The checkpoint filename is `checkpoint_best_ema.pth`, pinned to revision `c59fd4f451b254501700a56c7769f1a3d788c753`. First load calls `hf_hub_download`, then constructs `RFDETRBase(pretrain_weights=checkpoint, num_classes=4)`. A compatibility fallback supports older RF-DETR versions exposing `.load()`. A non-`auto` configured device moves the internal Torch module explicitly; CPU is the default, regardless of whether the installed Torch build also supports CUDA.

Input is the shared processed RGB Pillow image. RF-DETR receives the confidence threshold and returns a Supervision-style detections object in the current runtime; a legacy iterable parser is retained. XYXY boxes and scores become `MarkDetection`, checkbox/unknown classes are filtered, and the adapter restores source bboxes. No polygon is emitted. Metadata retains source label/class ID and records ignored checkbox classes. Provenance includes module `stamp_signature`, backend `rfdetr`, model ID, and the pinned revision as `model_version`.

Limitations: the class-ID mapping is checkpoint-specific; there is no signature identity, stamp semantics, checkbox output, or overlap deduplication.

## Mock backends

The default example configuration uses `mock` for all modules. Mocks produce deterministic geometric objects and exercise preprocessing, coordinate restoration, aggregation, response schemas, visualization, and exports without loading model frameworks. Their content is not a quality evaluation and must not be mistaken for inferred results.

## Model download and cache audit

Audit date: 2026-09-07. The inspected environment contains PaddleOCR 3.7.0, PaddleX 3.7.2, PaddlePaddle 3.2.0, RF-DETR 1.10.0, Hugging Face Hub 1.30.0, and Torch 2.14.0. Repository requirements use compatible ranges rather than pinning every installed patch version.

### Observed local storage

The existing real weights are not in the repository `models/` directory:

- PaddleX official models are under `~/.paddlex/official_models/`: `PP-OCRv5_server_det`, `arabic_PP-OCRv5_mobile_rec`, `PP-LCNet_x1_0_textline_ori`, and `PP-DocLayoutV3` (approximately 225 MB in the inspected environment).
- The RF-DETR checkpoint is in `~/.cache/huggingface/hub/models--bluecopa--rf-detr-stamp-signature-detector/` (approximately 352 MB), with a snapshot symlink for the pinned revision.
- Small Hugging Face repository references for the Paddle models also exist under `~/.cache/huggingface/hub`, but PaddleX's usable copied model directories are under its own cache.
- `~/.cache/paddle` exists for Paddle engine/dataset data; it is not the PaddleX official-model directory.

PaddleX reads `PADDLE_PDX_CACHE_HOME`, defaulting to `~/.paddlex`, and stores official downloads under `<cache>/official_models`. `PADDLE_HOME` is a separate Paddle runtime cache. Hugging Face Hub reads `HF_HOME`, defaulting to `~/.cache/huggingface`; an explicit `WIKI_HAMI_STAMP_SIGNATURE_CACHE_DIR` overrides the cache directory only for the RF-DETR `hf_hub_download` call.

### Reuse and download frequency

PaddleX checks whether its named official-model directory already exists and reuses it. `hf_hub_download` uses its content-addressed cache for the pinned repository/revision/file. Backend `_load()` methods retain the constructed models, so normal requests do not call the download/load path again. With the shared runtime registry, independent endpoints and `/extract` use the same service/model objects.

Therefore:

```text
first real inference in a fresh cache -> download + initialize
later process start with same cache   -> reuse weights + initialize model in RAM
later request in same process         -> reuse weights and in-memory model
```

There is no per-request redownload. A deployment with multiple worker processes still initializes one model set per worker and multiplies RAM/VRAM use.

### Why `models/` is empty

Framework-managed public weights belong in framework caches and are intentionally excluded from Git. `models/` is reserved for explicitly exported/fine-tuned project assets and policy documentation. It should remain a placeholder unless Wiki Hami begins shipping a project-owned local checkpoint. Point `PADDLE_PDX_CACHE_HOME`/`HF_HOME` at a persistent cache rather than copying downloaded weights into Git.

### Container persistence

The Docker image defaults all caches below `/app/.cache`. Local Compose mounts the named `wiki_hami_model_cache` volume at that root. Production Compose maps `${WIKI_HAMI_DATA_ROOT:-/var/lib/wiki-hami}/cache` and sets explicit PaddleX/Paddle/Hugging Face subpaths. These mounts survive container replacement. This corrects an earlier configuration that persisted `PADDLE_HOME` but omitted PaddleX's actual `PADDLE_PDX_CACHE_HOME`.

No dedicated warmup command or readiness endpoint exists. To prewarm, start the API with real backends and send one representative image to each independent module endpoint (or one `/extract` call); wait for completion before admitting production traffic. Network access is required only when a configured cache lacks the requested assets.
