# Computer Vision – Contract v0

This schema normalizes CV pipeline telemetry across phases:
`ingest`, `preprocess`, `inference`, `postprocess`, `eval`, `serve`, `track`, `pose`.

## Controlled vocabulary
- `level`, `category`, `outcome`, `safety_flags` are shared via `schemas/_common.json`.
- Use `category: "cv"` for this contract.

## Units
- All latencies must be **milliseconds** in `latency_ms`.
- If a raw message uses seconds or microseconds, convert:
  - `0.85s` → `850`
  - `1200µs` → `1.2`
  - `3.2ms` → `3.2` (unchanged)

## Fields (high level)
- **phase**: one of `ingest`, `preprocess`, `inference`, `postprocess`, `eval`, `serve`, `track`, `pose`
- **outcome**: controlled vocabulary (`success`, `failure`, `running`, `timeout`, `cancelled`, `pending`)
- **metrics**: standard metrics plus `metrics.extra{}` for extensions
- **hardware**: string _or_ object `{ accelerator (req), runtime?, memory_gb?, component?, level? }`
- **meta**: provenance `{ raw_message, parse{ parser_name, parser_version, pattern_id, ok? } }`
- **component** (optional): a logical component label at the event level (e.g., `"classifier"`)

---

## Raw → JSON examples (per phase)

### 1) `ingest` (bulk import; custom metric via `metrics.extra`)
**raw**
```
ingest files=250000 took=1.2s
```
**json**
```json
{
  "phase": "ingest",
  "component": "loader",
  "level": "info",
  "category": "cv",
  "outcome": "success",
  "model_name": "n/a",
  "dataset_id": "retail_cameras_2025w40",
  "image_count": 250000,
  "metrics": { "extra": { "files_processed": 250000 } },
  "latency_ms": 1200,
  "batch_size": 1000,
  "hardware": "CPU / Python 3.12",
  "meta": {
    "raw_message": "ingest files=250000 took=1.2s",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.ingest.001", "ok": true }
  }
}
```

### 2) `preprocess` (ms already)
**raw**
```
preproc resize=640x640 latency_ms=3.2
```
**json**
```json
{
  "phase": "preprocess",
  "component": "resize",
  "level": "debug",
  "category": "cv",
  "outcome": "success",
  "model_name": "yolov8n",
  "dataset_id": "coco_train",
  "image_count": 64000,
  "metrics": { "extra": { "resize": "640x640" } },
  "latency_ms": 3.2,
  "batch_size": 64,
  "hardware": { "accelerator": "CPU", "runtime": "NumPy 2.0", "memory_gb": 8 },
  "meta": {
    "raw_message": "preproc resize=640x640 latency_ms=3.2",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.pre.001", "ok": true }
  }
}
```

### 3) `inference` (seconds → ms)
**raw**
```
model=vit_b16 ds=imagenet_val bs=32 latency=0.085s acc=0.88 fps=375
```
**json**
```json
{
  "phase": "inference",
  "component": "classifier",
  "level": "info",
  "category": "cv",
  "outcome": "success",
  "model_name": "vit_b16",
  "dataset_id": "imagenet_val",
  "image_count": 2000,
  "metrics": { "accuracy": 0.88, "fps": 375 },
  "latency_ms": 85,
  "batch_size": 32,
  "hardware": { "accelerator": "NVIDIA A100", "runtime": "PyTorch 2.4", "memory_gb": 40 },
  "meta": {
    "raw_message": "model=vit_b16 ds=imagenet_val bs=32 latency=0.085s acc=0.88 fps=375",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.infer.001", "ok": true }
  }
}
```

### 4) `postprocess` (ms already)
**raw**
```
nms thresh=0.6 latency_ms=2.1
```
**json**
```json
{
  "phase": "postprocess",
  "component": "nms",
  "level": "info",
  "category": "cv",
  "outcome": "success",
  "model_name": "yolov5s",
  "dataset_id": "coco_val",
  "image_count": 2000,
  "metrics": { "extra": { "nms_threshold": 0.6 } },
  "latency_ms": 2.1,
  "batch_size": 16,
  "hardware": "CUDA / PyTorch 2.4",
  "meta": {
    "raw_message": "nms thresh=0.6 latency_ms=2.1",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.post.001", "ok": true }
  }
}
```

### 5) `eval` (µs → ms)
**raw**
```
ds=cityscapes ap50=0.78 iou=0.66 latency=1200µs
```
**json**
```json
{
  "phase": "eval",
  "level": "info",
  "category": "cv",
  "outcome": "success",
  "model_name": "deeplabv3",
  "dataset_id": "cityscapes",
  "image_count": 500,
  "metrics": { "ap50": 0.78, "iou": 0.66 },
  "latency_ms": 1.2,
  "batch_size": 8,
  "hardware": "NVIDIA V100 / TF 2.16",
  "meta": {
    "raw_message": "ds=cityscapes ap50=0.78 iou=0.66 latency=1200µs",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.eval.001", "ok": true }
  }
}
```

### 6) `serve` (s → ms) failure
**raw**
```
HTTP 500 latency=0.9s message="OOM on GPU0"
```
**json**
```json
{
  "phase": "serve",
  "level": "error",
  "category": "cv",
  "outcome": "failure",
  "model_name": "resnet50",
  "dataset_id": "imagenet_val",
  "image_count": 128,
  "metrics": { "fps": 0 },
  "latency_ms": 900,
  "batch_size": 1,
  "hardware": { "accelerator": "NVIDIA T4", "runtime": "Triton 24.08", "memory_gb": 16 },
  "error": { "message": "OOM on GPU0" },
  "meta": {
    "raw_message": "HTTP 500 latency=0.9s message=\"OOM on GPU0\"",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.serve.500", "ok": true }
  }
}
```

### 7) `track` (ms) partial
**raw**
```
tracker=bytetrack map=0.62 fps=120 latency=7ms
```
**json**
```json
{
  "phase": "track",
  "component": "bytetrack",
  "level": "warn",
  "category": "cv",
  "outcome": "pending",
  "model_name": "yolov7",
  "dataset_id": "mot17",
  "image_count": 10000,
  "metrics": { "map": 0.62, "fps": 120 },
  "latency_ms": 7,
  "batch_size": 8,
  "hardware": "RTX 3080 / Torch 2.3",
  "meta": {
    "raw_message": "tracker=bytetrack map=0.62 fps=120 latency=7ms",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.track.001", "ok": true }
  }
}
```

### 8) `pose` (ms)
**raw**
```
pose=hrnet ap=0.71 latency_ms=5.5
```
**json**
```json
{
  "phase": "pose",
  "component": "keypoints",
  "level": "info",
  "category": "cv",
  "outcome": "success",
  "model_name": "hrnet_w32",
  "dataset_id": "coco_keypoints",
  "image_count": 5000,
  "metrics": { "ap": 0.71 },
  "latency_ms": 5.5,
  "batch_size": 32,
  "hardware": { "accelerator": "NVIDIA A10", "runtime": "ONNX Runtime 1.18", "memory_gb": 24 },
  "meta": {
    "raw_message": "pose=hrnet ap=0.71 latency_ms=5.5",
    "parse": { "parser_name": "ulog", "parser_version": "1.0.0", "pattern_id": "cv.pose.001", "ok": true }
  }
}
```
