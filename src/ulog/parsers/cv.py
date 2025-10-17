"""Computer Vision domain parser for image/video processing logs."""

import re
from typing import Dict, Any, Optional, List

from .base import BaseParser, ParseResult
from ..patterns.base import Pattern, FieldExtraction


class DataLoadPattern(Pattern):
    """Matches [Data] {message} format for data loading and video/image I/O.
    
    Examples:
    - [Data] Opening video source: file:///data/videos/store_cam_01.mp4
    - [Data] Opened stream 1920x1080 @ 29.97fps (H.264, yuv420p)
    - [Data] RTSP connect rtsp://10.0.0.50/stream1 ... failed: timeout (attempt 1/5, backoff 2s)
    - [Data][WARNING] Non-monotonous DTS in output stream 0:1; frame drop may occur
    - [Data][ERROR] Could not open image '/data/frames/000123.png': No such file or directory
    """
    
    pattern_id = "cv_data_load"
    confidence = 0.95
    
    regex = re.compile(
        r'\[Data\](?:\[(?P<level>INFO|WARNING|ERROR|DEBUG|WARN)\])?\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match data loading pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category
            fields["category"] = "data_loading"
            
            # Infer level if not explicitly set
            if not fields.get("level"):
                message_lower = fields.get("message", "").lower()
                if "error" in message_lower or "failed" in message_lower or "could not" in message_lower:
                    fields["level"] = "error"
                elif "warning" in message_lower or "warn" in message_lower:
                    fields["level"] = "warning"
                else:
                    fields["level"] = "info"
            
            # Determine outcome based on level and message content
            message_lower = fields.get("message", "").lower()
            if fields["level"] == "error" or "failed" in message_lower:
                fields["outcome"] = "failure"
            else:
                fields["outcome"] = "success"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|([^\s,;]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class PreprocPattern(Pattern):
    """Matches [Preproc] {message} format for preprocessing operations.
    
    Examples:
    - [Preproc] Letterbox resize 1920x1080 -> 640x640 (pad: 0x160 top/bottom)
    - [Preproc][WARNING] Non-contiguous array; making contiguous copy (HWC->CHW)
    - [Preproc] Normalizing to [0,1], dtype float32
    - [Preproc][ERROR] Invalid image shape: expected 3 channels, got 1 (grayscale)
    """
    
    pattern_id = "cv_preproc"
    confidence = 0.95
    
    regex = re.compile(
        r'\[Preproc\](?:\[(?P<level>INFO|WARNING|ERROR|DEBUG|WARN)\])?\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match preprocessing pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category
            fields["category"] = "preprocessing"
            
            # Infer level if not explicitly set
            if not fields.get("level"):
                message_lower = fields.get("message", "").lower()
                if "error" in message_lower or "invalid" in message_lower:
                    fields["level"] = "error"
                elif "warning" in message_lower or "warn" in message_lower:
                    fields["level"] = "warning"
                else:
                    fields["level"] = "info"
            
            # Determine outcome based on level
            if fields["level"] == "error":
                fields["outcome"] = "failure"
            else:
                fields["outcome"] = "success"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|([^\s,;]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class ModelPattern(Pattern):
    """Matches [Model] {message} format for model loading and operations.
    
    Examples:
    - [Model] Loading PyTorch weights: /models/yolov8s.pt (anchors auto)
    - [Model] Device selected: cuda:0 (NVIDIA RTX A5000, 24GB) — CUDA 12.2, cuDNN 9.0
    - [Model][WARNING] Missing keys in state_dict: model.head.cls_conv.2.weight
    - [Model] Converting PyTorch -> ONNX opset=13 dynamic_axes=[batch,h,w]
    - [Model][ERROR] Shape mismatch: expected input [N,3,640,640], got [N,640,640,3]
    """
    
    pattern_id = "cv_model"
    confidence = 0.95
    
    regex = re.compile(
        r'\[Model\](?:\[(?P<level>INFO|WARNING|ERROR|DEBUG|WARN)\])?\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match model pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category
            fields["category"] = "model"
            
            # Infer level if not explicitly set
            if not fields.get("level"):
                message_lower = fields.get("message", "").lower()
                if "error" in message_lower or "failed" in message_lower:
                    fields["level"] = "error"
                elif "warning" in message_lower or "warn" in message_lower or "missing" in message_lower:
                    fields["level"] = "warning"
                else:
                    fields["level"] = "info"
            
            # Determine outcome based on level
            if fields["level"] == "error":
                fields["outcome"] = "failure"
            else:
                fields["outcome"] = "success"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values and arrays)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|(\[[^\]]*\])|([^\s,;]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4) or match.group(5)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class CVComponentPattern(Pattern):
    """Matches other CV component logs like [Infer], [Post], [Track], [Eval], etc.
    
    Examples:
    - [Infer] Warmup(3) done — mean 6.1ms (preproc 1.0 / infer 4.2 / post 0.9)
    - [Post] Raw detections: 32 — NMS(iou=0.50, conf=0.25) -> 15
    - [Track][DeepSORT] New track id=7 (cls=person conf=0.86)
    - [Eval] mAP@[0.50:0.95]=0.451 — AP50=0.693, AP75=0.497, AR=0.612
    - [HW] GPU memory usage: alloc=3.2GB reserved=4.0GB free=19.7GB
    - [Serve] Starting HTTP inference server on 10.0.0.1:9000
    """
    
    pattern_id = "cv_component_log"
    confidence = 0.85
    
    regex = re.compile(
        r'\[(?P<component>[^\]]+)\](?:\[(?P<subcomponent>[^\]]+)\])?(?:\[(?P<level>INFO|WARNING|ERROR|DEBUG|WARN)\])?\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("component", "component"),
        FieldExtraction("subcomponent", "subcomponent"),
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match CV component pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            component = fields.get("component", "").lower()
            
            # Map component to category
            if component in ["infer", "inference"]:
                fields["category"] = "inference"
            elif component in ["post", "postproc", "postprocess"]:
                fields["category"] = "postprocessing"
            elif component in ["track", "tracking"]:
                fields["category"] = "tracking"
            elif component in ["eval", "evaluation", "metrics"]:
                fields["category"] = "evaluation"
            elif component in ["hw", "hardware", "gpu", "cuda"]:
                fields["category"] = "hardware"
            elif component in ["serve", "server", "grpc"]:
                fields["category"] = "serving"
            elif component in ["config", "configuration"]:
                fields["category"] = "configuration"
            elif component in ["train", "training"]:
                fields["category"] = "training"
            elif component in ["aug", "augmentation"]:
                fields["category"] = "augmentation"
            elif component in ["onnxruntime", "tensorrt", "openvino"]:
                fields["category"] = "runtime"
            elif component in ["ocr"]:
                fields["category"] = "ocr"
            elif component in ["pose"]:
                fields["category"] = "pose_estimation"
            elif component in ["dbg", "debug"]:
                fields["category"] = "debug"
            elif component in ["security", "privacy"]:
                fields["category"] = "security"
            elif component in ["cli"]:
                fields["category"] = "cli"
            elif component in ["env", "environment"]:
                fields["category"] = "environment"
            else:
                fields["category"] = "general"
            
            # Check if subcomponent is actually a level indicator
            subcomp = fields.get("subcomponent", "")
            if subcomp and subcomp.upper() in ["INFO", "WARNING", "ERROR", "DEBUG", "WARN"]:
                if not fields.get("level"):
                    fields["level"] = subcomp.lower()
                fields.pop("subcomponent", None)
            
            # Infer level if not explicitly set
            if not fields.get("level"):
                message_lower = fields.get("message", "").lower()
                if "error" in message_lower or "failed" in message_lower or "cuda error" in message_lower:
                    fields["level"] = "error"
                elif "warning" in message_lower or "warn" in message_lower:
                    fields["level"] = "warning"
                else:
                    fields["level"] = "info"
            
            # Determine outcome based on level
            if fields["level"] == "error":
                fields["outcome"] = "failure"
            else:
                fields["outcome"] = "success"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values, arrays, and nested structures)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|(\[[^\]]*\])|({[^}]*})|([^\s,;]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4) or match.group(5) or match.group(6)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class CVParser(BaseParser):
    """Parser for Computer Vision domain logs.
    
    Handles image/video processing, model inference, tracking, and evaluation logs.
    """
    
    parser_name = "cv_parser"
    parser_version = "1.0.0"
    
    def __init__(self):
        """Initialize parser with patterns."""
        self.patterns: List[Pattern] = [
            DataLoadPattern(),
            PreprocPattern(),
            ModelPattern(),
            CVComponentPattern(),
        ]
    
    def parse(self, raw_message: str) -> ParseResult:
        """Parse a CV log message.
        
        Args:
            raw_message: Raw log message text
            
        Returns:
            ParseResult with extracted data or error
        """
        # Try each pattern in order of confidence
        best_match = None
        best_confidence = 0.0
        best_pattern_id = None
        
        for pattern in self.patterns:
            result = pattern.match(raw_message)
            if result is not None:
                if pattern.confidence > best_confidence:
                    best_match = result
                    best_confidence = pattern.confidence
                    best_pattern_id = pattern.pattern_id
        
        if best_match is not None:
            return ParseResult(
                success=True,
                data=best_match,
                pattern_id=best_pattern_id,
                confidence=best_confidence,
                error=None,
                unparsed_reason=None
            )
        else:
            return ParseResult(
                success=False,
                data=None,
                pattern_id=None,
                confidence=0.0,
                error="no_pattern_match",
                unparsed_reason="no_pattern_match"
            )
    
    def get_patterns(self) -> List[Pattern]:
        """Return list of patterns this parser supports."""
        return self.patterns
