"""Tests for CV parser."""
from ulog.parsers.cv import CVParser


class TestCVParser:
    def setup_method(self):
        self.parser = CVParser()

    def test_data_open_success(self):
        log = "[Data] Opening video source: file:///data/videos/store_cam_01.mp4"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "cv_data_load"
        assert res.data["category"] == "data_loading"
        assert res.data["outcome"] == "success"

    def test_data_error(self):
        log = "[Data][ERROR] Could not open image '/data/frame.png': No such file or directory"
        res = self.parser.parse(log)
        assert res.success
        assert res.data["level"] == "error"
        assert res.data["outcome"] == "failure"

    def test_preproc_warning(self):
        log = "[Preproc][WARNING] Non-contiguous array; making contiguous copy (HWC->CHW)"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "cv_preproc"
        assert res.data["category"] == "preprocessing"

    def test_model_info(self):
        log = "[Model] Loading PyTorch weights: /models/yolov8s.pt (anchors auto)"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "cv_model"
        assert res.data["category"] == "model"

    def test_infer_component(self):
        log = "[Infer] Warmup(3) done — mean 6.1ms (preproc 1.0 / infer 4.2 / post 0.9)"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "cv_component_log"
        assert res.data["category"] == "inference"
