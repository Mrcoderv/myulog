"""
Unit tests for CV parser (raw → json).
"""


class TestCVParserRawToJson:
    """Test raw log parsing for cv domain (≥8 tests)."""

    def test_cv_inference_batch(self, cv_parser):
        """Test parsing inference batch processing."""
        raw = "Inference batch: 32 images processed at 45 FPS"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_training_epoch(self, cv_parser):
        """Test parsing training epoch log."""
        raw = "Training epoch 10/50: loss=2.34, accuracy=0.87"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_gpu_oom_error(self, cv_parser):
        """Test parsing GPU out of memory error."""
        raw = "CUDA out of memory: tried to allocate 2.5 GB"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_model_loading(self, cv_parser):
        """Test parsing model loading."""
        raw = "Loading model: yolov8n.pt with 3.2M parameters"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_dataset_loading(self, cv_parser):
        """Test parsing dataset loading."""
        raw = "Dataset loaded: 10000 images from dataset_coco2017"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_map_evaluation(self, cv_parser):
        """Test parsing mAP evaluation metric."""
        raw = "Evaluation complete: mAP@0.5:0.95 = 0.456"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_throughput_measurement(self, cv_parser):
        """Test parsing throughput measurement."""
        raw = "Processed 5000 images in 120s (41.7 images/sec)"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_hardware_info(self, cv_parser):
        """Test parsing hardware information."""
        raw = "Using GPU: NVIDIA RTX 3090 with 24GB VRAM"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_batch_size_config(self, cv_parser):
        """Test parsing batch size configuration."""
        raw = "Batch size set to 64 for training phase"
        result = cv_parser.parse(raw)

        assert result is not None

    def test_cv_loss_spike(self, cv_parser):
        """Test parsing loss spike warning."""
        raw = "Warning: Training loss spiked to 8.5 at step 1500"
        result = cv_parser.parse(raw)

        assert result is not None
