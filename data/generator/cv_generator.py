from generator import GenerateLog


class GenerateCVLog(GenerateLog):
    def __init__(
        self,
        fields: list[str],
        size: int,
        seed: int,
        input_params: list[str] | None,
        valid_params: list[str],
    ) -> None:
        super().__init__(fields, size, seed, valid_params)

        self.frameworks = ["PyTorch", "TensorFlow", "ONNX", "Keras", "OpenVINO"]
        self.accelerators = [
            "NVIDIA A100",
            "NVIDIA V100",
            "Google TPU v3",
            "Intel Xeon",
            "AMD MI100",
        ]
        self.metrics_names = [
            "accuracy",
            "loss",
            "precision",
            "recall",
            "f1_score",
            "mAP",
            "fps",
            "iou",
            "ap50",
            "ap",
        ]
        self.phases = ["ingest", "preprocess", "inference", "postprocess", "eval", "serve", "track", "pose"]
        self.models = ["ResNet50", "VGG16", "InceptionV3", "MobileNetV2", "EfficientNetB0"]
        self.datasets = ["ImageNet", "CIFAR-10", "COCO", "MNIST", "Pascal VOC"]
        self.outcomes = self.load_from_vocab(["outcomes"])[0]
        self.input_params = input_params if input_params else []
        self.param_dict = {}

    def generate_metrics(self):
        quality = self.generate_float(0.6, 0.99)
        metrics = {}
        metrics["fps"] = round(self.generate_float(20, 120) * (0.8 + (1 - quality) * 0.2), 2)
        metrics["accuracy"] = round(min(quality + self.generate_float(-0.05, 0.05), 1), 4)
        metrics["precision"] = round(min(quality + self.generate_float(-0.05, 0.05), 1), 4)
        metrics["recall"] = round(min(quality + self.generate_float(-0.05, 0.05), 1), 4)
        p, r = metrics["precision"], metrics["recall"]
        metrics["f1_score"] = round(2 * p * r / (p + r + 1e-6), 4)
        metrics["iou"] = round(
            min(
                (metrics["f1_score"] + metrics["recall"]) / 2 + self.generate_float(-0.05, 0.05),
                1,
            ),
            4,
        )
        metrics["ap50"] = round(
            min(metrics["iou"] + self.generate_float(-0.05, 0.05), 1),
            4,
        )
        metrics["ap"] = round(
            min(
                (metrics["precision"] + metrics["recall"]) / 2 + self.generate_float(-0.05, 0.05),
                1,
            ),
            4,
        )
        metrics["map"] = round(min((metrics["ap"] + metrics["ap50"]) / 2 + self.generate_float(-0.02, 0.02), 1), 4)

        # Random subset for variation
        sample_count = self.generate_integer(1, len(self.metrics_names))
        sample = self.random.sample(self.metrics_names, sample_count)
        return {k: v for k, v in metrics.items() if k in sample}

    def generate_log_entry(self):
        logs = []
        for _ in range(self.size):
            log = {
                "phase": self.select_enum(self.phases),
                "model_name": self.select_enum(self.models),
                "dataset_id": self.select_enum(self.datasets),
                "image_count": self.generate_integer(1, 10000),
                "metrics": self.generate_metrics(),
                "timestamp": self.generate_timestamp(),
                "latency_ms": self.generate_float(0, 100.0),
                "batch_size": self.generate_integer(1, 128),
                "hardware": {"accelerator": self.select_enum(self.accelerators)},
                "outcome": self.select_enum(self.outcomes),
                "meta": {
                    "raw_message": None,
                    "parse": {
                        "parse_name": self.generate_string(10),
                        "parser_version": self.select_enum(["1.0.0", "1.1.0", "2.0.0"]),
                        "pattern_id": self.generate_unique_string(),
                    },
                },
            }

            # populate raw_message after the log dict exists so context is available
            # Build parser-friendly CV raw messages with bracketed components and key=value parts
            log["meta"]["raw_message"] = self._build_cv_raw_message(log)

            if log["outcome"] == "failure":
                # use domain-aware message generator for realistic error messages
                log["error"] = {"message": self.generate_message(domain="cv", word_count=self.generate_integer(6, 24))}

            if self.input_params:
                log = self.generate_option_params(log)

            logs.append(log)

        return logs

    def _build_cv_raw_message(self, log: dict) -> str:
        """Compose a parsable CV raw message that matches parser patterns.

        Examples produced:
        - [Infer] Inference: ResNet50 processed 32 images on NVIDIA V100 - avg_latency=71.60ms fps=14.03 batch=8
        - [Model] Device selected: cuda:0 (NVIDIA V100, 16GB)
        - [Data] Processed 4013 images from COCO: path=/data/coco images=4013
        - [Eval] mAP@[0.50:0.95]=0.451 — AP50=0.693, AP75=0.497, AR=0.612
        """
        phase = log.get("phase", "inference")
        model = log.get("model_name")
        dataset = log.get("dataset_id")
        images = log.get("image_count")
        latency = round(log.get("latency_ms", self.generate_float(1, 200)), 3)
        metrics = log.get("metrics") or {}

        # Map phase to component tag
        phase_to_component = {
            "ingest": "Data",
            "preprocess": "Preproc",
            "inference": "Infer",
            "postprocess": "Post",
            "eval": "Eval",
            "track": "Track",
            "pose": "Pose",
            "hw": "HW",
            "model": "Model",
            "serve": "Serve",
            "config": "Config",
            "aug": "Aug",
        }

        comp = phase_to_component.get(phase, "Infer")

        # DATA / INGEST variants
        if comp == "Data":
            variants = [
                lambda: f"Opening video source: {self.faker.file_path(depth=3) if self.faker else 'file:///data/videos/cam.mp4'}",
                lambda: f"Opened stream {self.select_enum(['1920x1080','1280x720'])} @ {round(self.generate_float(24,30),2)}fps (H.264, yuv420p)",
                lambda: f"RTSP connect {self.select_enum(['rtsp://10.0.0.50/stream1','rtsp://10.0.0.51/stream2'])} ... failed: timeout (attempt {self.generate_integer(1,5)}/5, backoff {self.generate_integer(1,5)}s)",
                lambda: f"RTSP connected: {self.select_enum(['1280x720','1920x1080'])} @ {self.select_enum([25,30,29.97])}fps (H.265)",
                lambda: f"[WARNING] Unknown fourcc '{self.select_enum(['xvid','DIVX','MJPG'])}' — falling back to software decoder",
                lambda: f"[ERROR] Could not open image '{self.faker.file_path(depth=2) if self.faker else '/data/frames/000123.png'}': No such file or directory",
                lambda: f"[INFO] EXIF orientation={self.select_enum([3,6,1])} detected; rotating image {self.select_enum(['90° CW','90° CCW','180°'])}",
                lambda: f"[WARNING] Color space mismatch detected (BGR input) — converting to RGB",
            ]
            choice = self.select_enum(variants)
            text = choice()
            # many sample messages include an explicit [WARNING]/[ERROR] inside the bracketed tag
            if text.startswith('[WARNING]') or text.startswith('[ERROR]') or text.startswith('[INFO]'):
                return f"[Data]{text}"
            return f"[Data] {text}"

        # PREPROC
        if comp == "Preproc":
            variants = [
                lambda: f"Letterbox resize {self.select_enum(['1920x1080','1280x720'])} -> {self.select_enum(['640x640','320x320'])} (pad: 0x160 top/bottom)",
                lambda: f"Non-contiguous array; making contiguous copy (HWC->CHW)",
                lambda: f"Normalizing to [0,1], dtype float32",
                lambda: f"[ERROR] Invalid image shape: expected 3 channels, got {self.select_enum([1,2])} (grayscale)",
                lambda: f"[WARNING] NaN values found after standardization — replacing with 0.0",
            ]
            return f"[Preproc] {self.select_enum(variants)()}"

        # AUGMENTATION
        if comp == "Aug":
            return f"[Aug] Applied transforms: RandomFlip(p=0.5), ColorJitter(bright=0.2,contrast=0.2), Mosaic(p=0.2)"

        # MODEL / RUNTIME
        if comp == "Model":
            variants = [
                lambda: f"Loading PyTorch weights: /models/{self.select_enum(['yolov8s.pt','yolov8m.pt'])} (anchors auto)",
                lambda: f"Device selected: {self.select_enum(['cuda:0','cuda:1','cpu'])} ({self.select_enum(['NVIDIA RTX A5000, 24GB','NVIDIA V100, 16GB','Intel Xeon'])}) — CUDA {self.select_enum(['12.2','11.7'])}, cuDNN {self.select_enum(['9.0','8.2'])}",
                lambda: f"[WARNING] Missing keys in state_dict: model.head.cls_conv.2.weight ... (3 more); unexpected keys: model.neck.upsample.bias",
                lambda: f"Converting PyTorch -> ONNX opset=13 dynamic_axes=[batch,h,w]",
                lambda: f"[INFO] Exported ONNX graph: {self.generate_integer(100,300)} layers, {round(self.generate_float(1.0,20.0),1)} GFLOPs @640x640",
            ]
            return f"[Model] {self.select_enum(variants)()}"

        # ONNXRuntime / TensorRT style messages (use as component name if present)
        if comp == "HW":
            if self.random.random() < 0.3:
                alloc = round(self.generate_float(0.5, 16.0), 2)
                reserved = round(alloc + self.generate_float(0.1, 4.0), 2)
                free = round(self.generate_float(0.1, 24.0), 2)
                total = round(reserved + free, 2)
                return f"[HW] GPU memory usage: alloc={alloc}GB reserved={reserved}GB free={free}GB total={total}GB"
            return f"[HW][WARNING] GPU temperature {self.generate_integer(60,95)}°C — throttling clocks"

        # INFER messages (warmup, throughput, warnings, errors)
        if comp == "Infer":
            if self.random.random() < 0.12:
                # warmup
                mean = round(self.generate_float(1.0, 12.0), 1)
                return f"[Infer] Warmup({self.generate_integer(1,5)}) done — mean {mean}ms (preproc {round(mean*0.15,1)} / infer {round(mean*0.7,1)} / post {round(mean*0.15,1)})"
            if self.random.random() < 0.18:
                b = self.select_enum([4,8,16])
                throughput = self.generate_integer(30, 600)
                return f"[Infer] Batch={b} throughput={throughput} FPS — p50 {round(self.generate_float(1,20),1)}ms p95 {round(self.generate_float(5,30),1)}ms p99 {round(self.generate_float(10,50),1)}ms"
            if self.random.random() < 0.08:
                return f"[Infer][ERROR] CUDA error: device-side assert triggered at nms_cuda.cu:{self.generate_integer(100,300)}"
            # default inference line with breakdown
            batch = log.get("batch_size", self.select_enum([1,2,4,8]))
            fps = round(self.generate_float(5, 300), 2)
            return f"[Infer] Inference: {model} processed {images} images — avg latency {latency}ms batch={batch} fps={fps}"

        # POSTPROCESS
        if comp == "Post":
            detections = self.generate_integer(0, 128)
            nms_conf = round(self.generate_float(0.1, 0.5), 2)
            return f"[Post] Raw detections: {detections} — NMS(iou=0.50, conf={nms_conf}) -> {max(0,int(detections*0.5))}"

        # TRACK
        if comp == "Track":
            if self.random.random() < 0.5:
                tid = self.generate_integer(1, 200)
                cls = self.select_enum(["person","car","bicycle"])
                conf = round(self.generate_float(0.4, 0.99), 2)
                bbox = f"x1={self.generate_integer(0,640)},y1={self.generate_integer(0,480)},x2={self.generate_integer(640,1280)},y2={self.generate_integer(480,960)}"
                return f"[Track][DeepSORT] New track id={tid} (cls={cls} conf={conf}) @ ({bbox})"
            return f"[Track][DeepSORT] Lost track id={self.generate_integer(1,200)} (age={self.generate_integer(1,100)}, hits={self.generate_integer(1,10)}) — state: Tentative"

        # POSE
        if comp == "Pose":
            return f"[Pose][INFO] FPS={self.generate_integer(30,200)} on {self.select_enum(['cuda:0','cpu'])} — avg kp error (MPII) {round(self.generate_float(1.0,8.0),1)}px"

        # EVAL
        if comp == "Eval":
            if self.random.random() < 0.4:
                return f"[Eval] Running COCO mAP on val split (images={self.generate_integer(100,5000)}, iou=0.50:0.95)"
            ap50 = round(metrics.get("ap50", self.generate_float(0.4, 0.9)), 3)
            ap75 = round(metrics.get("ap75", self.generate_float(0.2, 0.7)), 3)
            mapv = round(metrics.get("map", round((ap50 + ap75) / 2, 3)), 3)
            return f"[Eval] mAP@[0.50:0.95]={mapv} — AP50={ap50}, AP75={ap75}, AR={round(self.generate_float(0.4,0.8),3)}"

        # DEFAULT / FALLBACK
        return f"[{comp}] {self.generate_message(domain='cv', word_count=12, context=log)}"

    def generate_option_params(self, log: dict) -> dict:
        for param in self.input_params:
            match param:
                case "timestamp":
                    log["timestamp"] = self.generate_timestamp()
                case "component":
                    log["component"] = self.generate_string(10)
                case "safety_flag":
                    log["safety_flag"] = self.select_enum(self.param_dict["safety_flags"])
                case "category":
                    log["category"] = self.select_enum(self.param_dict["categories"])
                case "level":
                    log["level"] = self.select_enum(self.param_dict["levels"])
                case "ok":
                    log["meta"]["parse"]["ok"] = self.select_enum([True, False])
                case _:
                    continue
        return log

    def verify_input_params(self) -> list[str]:
        verified = []
        for p in self.input_params:
            if self.verify_option_params(p, self.valid_params):
                verified.append(p)
            else:
                self.logger.warning(f"Unknown option param: {p}")
        return verified

    def run(self):
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        valid = self.generate_log_entry()
        invalid = self.generate_log_entry()
        for log in invalid:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]
        return valid, invalid
