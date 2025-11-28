"""
Synthetic test data generators for E2E validation tests
Generates realistic test data for all 4 domains
"""

from datetime import datetime, timedelta
import json
from typing import Dict, List


class SyntheticDataGenerator:
    """Generate synthetic test data"""

    @staticmethod
    def generate_core_api_logs(count: int = 10) -> List[str]:
        """Generate synthetic Core/API logs"""
        logs = []
        endpoints = [
            "/api/users",
            "/api/posts",
            "/api/comments",
            "/api/auth/login",
            "/api/auth/logout"
        ]
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for i in range(count):
            log = {
                "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                "endpoint": endpoints[i % len(endpoints)],
                "method": methods[i % len(methods)],
                "status_code": 200 + (i % 3) * 100,  # 200, 300, 400
                "response_time_ms": 50 + (i * 10),
                "user_id": f"user_{i}",
                "request_id": f"req_{i}",
            }
            logs.append(json.dumps(log))

        return logs

    @staticmethod
    def generate_llm_logs(count: int = 10) -> List[str]:
        """Generate synthetic LLM logs"""
        logs = []
        models = ["gpt-4", "gpt-3.5-turbo", "claude-2", "palm-2"]
        tasks = ["summarization", "translation", "question-answering", "text-generation"]

        for i in range(count):
            log = {
                "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                "model": models[i % len(models)],
                "task": tasks[i % len(tasks)],
                "prompt": f"This is a test prompt number {i}",
                "response": f"This is a test response number {i}",
                "tokens_used": 100 + (i * 5),
                "latency_ms": 200 + (i * 20),
                "success": True if i % 3 != 0 else False,
            }
            logs.append(json.dumps(log))

        return logs

    @staticmethod
    def generate_agentic_logs(count: int = 10) -> List[str]:
        """Generate synthetic Agentic logs"""
        logs = []
        agents = ["agent_1", "agent_2", "agent_3"]
        actions = ["think", "act", "observe", "plan", "execute"]

        for i in range(count):
            log = {
                "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                "agent_id": agents[i % len(agents)],
                "action": actions[i % len(actions)],
                "state": f"state_{i}",
                "reward": float(100 - i),
                "episode": i // 5,
                "step": i % 5,
            }
            logs.append(json.dumps(log))

        return logs

    @staticmethod
    def generate_cv_logs(count: int = 10) -> List[str]:
        """Generate synthetic Computer Vision logs"""
        logs = []
        tasks = ["object_detection", "image_classification", "segmentation", "pose_estimation"]
        statuses = ["success", "partial_success", "failed"]

        for i in range(count):
            log = {
                "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                "image_id": f"img_{i}",
                "task": tasks[i % len(tasks)],
                "status": statuses[i % len(statuses)],
                "inference_time_ms": 150 + (i * 10),
                "num_detections": 5 + i,
                "confidence_scores": [0.85 + (j * 0.01) for j in range(3)],
            }
            logs.append(json.dumps(log))

        return logs

    @staticmethod
    def generate_all_domains(count_per_domain: int = 10) -> Dict[str, List[str]]:
        """Generate test data for all domains"""
        return {
            "core_api": SyntheticDataGenerator.generate_core_api_logs(count_per_domain),
            "llm": SyntheticDataGenerator.generate_llm_logs(count_per_domain),
            "agentic": SyntheticDataGenerator.generate_agentic_logs(count_per_domain),
            "cv": SyntheticDataGenerator.generate_cv_logs(count_per_domain),
        }
