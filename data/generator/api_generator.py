from random import Random

from ULog.data.generator.generator import GenerateLog


class GenerateAPILog(GenerateLog):

    def __init__(self, fields, size, seed):
        super().__init__(fields, size, seed)
        self.methods = ["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS","INTERNAL"]
        self.statuses = ["success", "error", "timeout", "rejected", "throttled"]
        self.env = ["production", "staging", "development", "test"]
        self.errors = ["AUTH_INVALID_CREDENTIALS", "DB_CONNECTION_FAILED", 
                       "TIMEOUT_ERROR", "RATE_LIMIT_EXCEEDED"]
        self.error_messages = {
            "AUTH_INVALID_CREDENTIALS": "Invalid credentials provided.",
            "DB_CONNECTION_FAILED": "Failed to connect to the database.",
            "TIMEOUT_ERROR": "The request timed out.",
            "RATE_LIMIT_EXCEEDED": "Rate limit has been exceeded."
        }

        Random.seed(self.seed)
    def generate_endpoint(self) -> str:
        endpoints = [
            "/api/v1/resource",
            "/api/v1/resource/2",
            "/api/v1/resource/2/action",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
        ]
        return self.select_enum(endpoints)
    
    def GenerateLogEntry(
        self
    ):
        logs = []
        for _ in range(self.size):
            log_entry = {
                "request_id": self.generate_unique_string(),
                "timestamp": self.generate_timestamp(),
                "service": self.generate_string(100),
                "endpoint": self.generate_endpoint(),
                "action" : self.select_enum(self.methods),
                "result": self.select_enum(self.statuses),
                "latency_ms": self.generate_float(0, 5000.0),
                "env" : self.select_enum(self.env)
            }
            if log_entry["result"] in ["error", "timeout", "rejected"]:
                error_code = self.select_enum(self.errors)
                log_entry["error"] = {"code": error_code, 
                                      "message": self.error_messages[error_code]
                                      }
            logs.append(log_entry)
        return logs

    def run(self):
        valid_logs = self.GenerateLogEntry()
        unvalid_logs = self.GenerateLogEntry()
        for log in unvalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, unvalid_logs

