
from generator import GenerateLog


class GenerateCVLog(GenerateLog):
    def __init__(self, fields, size, seed):
        super().__init__(fields, size, seed)
        self.statuses = ["success", "partial", "failure"]
        self.frameworks = ["PyTorch", "TensorFlow", "ONNX", "Keras", "OpenVINO"]
        self.devices = ["CPU", "GPU", "TPU", "Jetson", "ASIC"]
        self.metrics = ["accuracy", "loss", "precision", "recall", "f1-score", "mAP"]
        self.phases = ["training", "inference", "evaluation"]
        self.models = ["ResNet50", "VGG16", "InceptionV3", "MobileNetV2", "EfficientNetB0"]
        self.datasets = ["ImageNet", "CIFAR-10", "COCO", "MNIST", "Pascal VOC"]

    def generate_metrics(self):
        """Generate a realistic set of CV metrics."""
        quality = self.generate_float(0.6, 0.99)  # good models hover high

        metrics = {}

        metrics["accuracy"] = round(quality + self.generate_float(-0.05, 0.05), 4)
        metrics["loss"] = round((1 - quality) * 2 + self.generate_float(0, 0.3), 4)

        metrics["precision"] = round(min(max(quality + self.generate_float(-0.05, 0.05), 0), 1), 4)
        metrics["recall"] = round(min(max(quality + self.generate_float(-0.05, 0.05), 0), 1), 4)

        p, r = metrics["precision"], metrics["recall"]
        metrics["f1-score"] = round(2 * p * r / (p + r + 1e-6), 4)

        metrics["mAP"] = (round(min(max(metrics["f1-score"] + 
                                        self.generate_float(-0.05, 0.05), 0),
                                    1),
                                4)
                        )

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
                    "device": self.select_enum(self.devices),
                    "framework": self.select_enum(self.frameworks),
                    "memory_gb": self.generate_float(0.0, 64.0),
                },
                "result": self.select_enum(self.statuses),
            }
            if log_entry["result"] == "failure":
                length = self.generate_integer(1,  500)
                log_entry["error"] = {"message": self.generate_string(length)}
            logs.append(log_entry)
        return logs

    def run(self):
        """Generate valid and invalid log entries."""
        valid_logs = self.generate_log_entry()
        unvalid_logs = self.generate_log_entry()
        for log in unvalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, unvalid_logs


