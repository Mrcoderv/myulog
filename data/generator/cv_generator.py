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

        self.statuses = ["success", "partial", "failure"]
        self.frameworks = ["PyTorch", "TensorFlow", "ONNX", "Keras", "OpenVINO"]
        self.components = ["CPU", "GPU", "TPU", "Jetson", "ASIC"]
        self.runtimes = ["TensorRT", "OpenVINO", "CUDA", "DirectML", "ROCm"]
        self.accelerators = [
            "NVIDIA A100",
            "NVIDIA V100",
            "Google TPU v3",
            "Intel Xeon",
            "AMD MI100",
        ]
        self.levels = ["device", "host", "cluster", "edge", "cloud"]

        self.metrics = [
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

        self.phases = [
            "ingest",
            "preprocess",
            "inference",
            "postprocess",
            "eval",
            "serve",
            "track",
            "pose",
        ]
        self.models = ["ResNet50", "VGG16", "InceptionV3", "MobileNetV2", "EfficientNetB0"]
        self.datasets = ["ImageNet", "CIFAR-10", "COCO", "MNIST", "Pascal VOC"]
        self.outcomes = self.load_from_vocab(["outcome"])[0]
        self.input_params = input_params if input_params else []
        self.param_dict = {}

    def generate_metrics(self):
        """Generate a realistic and internally consistent set of CV metrics."""

        # Base quality factor (represents how good the model is overall)
        quality = self.generate_float(0.6, 0.99)  # good models hover high
        metrics = {}

        metrics["fps"] = round(self.generate_float(20, 120) * (0.8 + (1 - quality) * 0.2), 2)

        metrics["accuracy"] = round(min(quality + self.generate_float(-0.05, 0.05), 1), 4)
        metrics["precision"] = round(min(quality + self.generate_float(-0.05, 0.05), 1), 4)
        metrics["recall"] = round(min(quality + self.generate_float(-0.05, 0.05), 1), 4)

        p, r = metrics["precision"], metrics["recall"]
        metrics["f1_score"] = round(2 * p * r / (p + r + 1e-6), 4)

        metrics["iou"] = round(
            min(
                (metrics["f1_score"] + metrics["recall"]) / 2 + self.generate_float(-0.05, 0.05), 1
            ),
            4,
        )

        metrics["ap50"] = round(min(metrics["iou"] + self.generate_float(-0.05, 0.05), 1), 4)

        metrics["ap"] = round(
            min(
                (metrics["precision"] + metrics["recall"]) / 2 + self.generate_float(-0.05, 0.05), 1
            ),
            4,
        )

        metrics["map"] = round(
            min((metrics["ap"] + metrics["ap50"]) / 2 + self.generate_float(-0.02, 0.02), 1), 4
        )

        metrics["loss"] = round((1 - quality) * 2 + self.generate_float(0, 0.3), 4)

        # Optionally sample a subset of metrics for variability
        sample_count = self.generate_integer(1, len(self.metrics))
        sample = self.random.sample(self.metrics, sample_count)
        metrics = {k: v for k, v in metrics.items() if k in sample}

        return metrics

    def generate_log_entry(self):
        """Generate a list of log entries."""
        logs = []
        for _ in range(self.size):
            log_entry = {
                "phase": self.select_enum(self.phases),
                "model_name": self.select_enum(self.models),
                "dataset_id": self.select_enum(self.datasets),
                "image_count": self.generate_integer(1, 10000),
                "metrics": self.generate_metrics(),
                "timestamp": self.generate_timestamp(),
                "latency_ms": self.generate_float(0, 100.0),
                "batch_size": self.generate_integer(1, 128),
                "hardware": {
                    "accelerator": self.select_enum(self.accelerators),
                },
                "outcome": self.select_enum(self.outcomes),
                "meta": {
                    "raw_message": self.generate_string(10000),
                    "parse": {
                        "parse_name": self.generate_string(10),
                        "parser_version": self.select_enum(["1.0.0", "1.1.0", "2.0.0"]),
                        "pattern_id": self.generate_unique_string(),
                    },
                },
            }
            if log_entry["outcome"] == "failure":
                length = self.generate_integer(1, 4096)
                log_entry["error"] = {"message": self.generate_string(length)}

            if self.input_params:
                log_entry = self.generate_option_params(log_entry)

            logs.append(log_entry)

        return logs

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
        verified_params = []
        for param in self.input_params:
            if self.verify_option_params(param, self.valid_params):
                verified_params.append(param)
            else:
                self.logger.warning(f"Unknown option param: {param}")
        return verified_params

    def run(self):
        """Generate valid and invalid log entries."""
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()
        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, invalid_logs
