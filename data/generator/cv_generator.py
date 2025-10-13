from random import Random

from ULog.data.generator.generator import GenerateLog


class GenerateCVLog(GenerateLog):

    def GenerateLogEntry(
        self, statuses, frameworks, devices, metrics, phases, models, datasets
    ):
        logs = []
        for _ in range(self.size):
            log_entry = {
                "phase": self.select_enum(phases),
                "model_name": self.select_enum(models),
                "dataset_id": self.select_enum(datasets),
                "image_count": self.generate_integer(1, 10000),
                "metrics": {self.select_enum(metrics): self.generate_float(0.0, 1.0)},
                "timestamp": self.generate_timestamp(),
                "latency_ms": self.generate_float(0, 100.0),
                "batch_size": self.generate_integer(1, 128),
                "hardware": {
                    "device": self.select_enum(devices),
                    "framework": self.select_enum(frameworks),
                    "memory_gb": self.generate_float(0.0, 64.0),
                },
                "result": self.select_enum(statuses),
            }
            if log_entry["result"] == "failure":
                length = self.generate_integer(1, 4096)
                log_entry["error"] = {"message": self.generate_string(length)}
            logs.append(log_entry)
        return logs

    def run(self):
        Random.seed(self.seed)
        statuses = ["success", "partial", "failure"]
        frameworks = ["PyTorch", "TensorFlow", "ONNX", "Keras", "OpenVINO"]
        devices = ["CPU", "GPU", "TPU", "Jetson", "ASIC"]
        metrics = ["accuracy", "loss", "precision", "recall", "f1-score", "mAP"]
        phases = ["training", "inference", "evaluation"]
        models = ["ResNet50", "VGG16", "InceptionV3", "MobileNetV2", "EfficientNetB0"]
        datasets = ["ImageNet", "CIFAR-10", "COCO", "MNIST", "Pascal VOC"]

        valid_logs = self.GenerateLogEntry(
            statuses, frameworks, devices, metrics, phases, models, datasets
        )
        unvalid_logs = self.GenerateLogEntry(
            statuses, frameworks, devices, metrics, phases, models, datasets
        )
        for log in unvalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, unvalid_logs


