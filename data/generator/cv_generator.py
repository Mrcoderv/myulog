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
                    "raw_message": self.generate_message(domain="cv", word_count=18),
                    "parse": {
                        "parse_name": self.generate_string(10),
                        "parser_version": self.select_enum(["1.0.0", "1.1.0", "2.0.0"]),
                        "pattern_id": self.generate_unique_string(),
                    },
                },
            }
            if log["outcome"] == "failure":
                log["error"] = {"message": self.generate_message(domain="cv", word_count=self.generate_integer(6, 24))}
            if self.input_params:
                log = self.generate_option_params(log)
            logs.append(log)
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
