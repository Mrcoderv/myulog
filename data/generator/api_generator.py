from typing import List

from generator import GenerateLog


class GenerateAPILog(GenerateLog):
    def __init__(
        self,
        fields: List[str],
        size: int,
        seed: int,
        input_params: List[str] | None,
        valid_options: List[str] | None,
    ) -> None:
        super().__init__(fields, size, seed, valid_options)
        self.input_params = input_params if input_params else []

        self.outcomes = self.load_from_vocab(["outcomes"])[0]

        self.actions = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "INTERNAL"]
        self.statuses = ["success", "error", "timeout", "rejected", "throttled"]
        self.env = ["production", "staging", "development", "test", "local"]
        self.errors = [
            "AUTH_INVALID_CREDENTIALS",
            "DB_CONNECTION_FAILED",
            "TIMEOUT_ERROR",
            "RATE_LIMIT_EXCEEDED",
        ]
        self.error_messages = {
            "AUTH_INVALID_CREDENTIALS": "Invalid credentials provided.",
            "DB_CONNECTION_FAILED": "Failed to connect to the database.",
            "TIMEOUT_ERROR": "The request timed out.",
            "RATE_LIMIT_EXCEEDED": "Rate limit has been exceeded.",
        }
        self.event_types = [
            "http_request",
            "http_response",
            "startup",
            "shutdown",
            "build",
            "dependency_install",
            "exception",
            "health_check",
        ]
        self.endpoints = [
            "/api/v1/resource",
            "/api/v1/resource/2",
            "/api/v1/resource/2/action",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
        ]
        self.dict_params = {}

    def select_status_code(self, result: str) -> int:
        if result == "success":
            return self.select_enum([200, 201, 202, 204])
        elif result == "error":
            return self.select_enum([400, 401, 403, 404, 500, 502, 503])
        elif result == "timeout":
            return 504
        elif result == "rejected":
            return 429
        elif result == "throttled":
            return 429
        else:
            return 500

    def generate_log_entry(self):
        logs = []
        for _ in range(self.size):
            log_entry = {
                "meta": {"raw_message": self.generate_string(10000)},
                "timestamp": self.generate_timestamp(),
                "event_type": self.select_enum(self.event_types),
                "service": self.generate_string(100),
                "env": self.select_enum(self.env),
                "outcome": self.select_enum(self.outcomes),
            }
            if log_entry["event_type"] in ["http_request", "http_response"]:
                log_entry["endpoint"] = self.select_enum(self.endpoints)
                log_entry["action"] = self.select_enum(self.actions)

            if log_entry["result"] in ["failure"]:
                type_of_error = self.select_enum(self.errors)
                choice_1 = {"type": type_of_error, "message": self.error_messages[type_of_error]}
                choice_2 = {"type": type_of_error}

                log_entry["error"] = self.select_enum([choice_1, choice_2])

            log_entry = self.generate_option_params(log_entry)
            logs.append(log_entry)
        return logs

    def generate_option_params(self, log: dict) -> dict:
        for param in self.input_params:
            match param:
                case "parse":
                    log["meta"]["parse_name"] = self.generate_string(10)
                    log["meta"]["parser_version"] = self.select_enum(["1.0.0", "1.1.0", "2.0.0"])
                    log["meta"]["pattern_id"] = self.generate_unique_string()
                    log["meta"]["confidence"] = self.generate_float(0, 1)

                case "level":
                    log["level"] = self.select_enum(self.dict_params["levels"])

                case "category":
                    log["category"] = self.select_enum(self.dict_params["categories"])

                case "sub_category":
                    log["sub_category"] = self.select_enum(self.dict_params["sub_categories"])

                case "component":
                    log["component"] = self.generate_string(self.generate_integer(1, 15))

                case "module":
                    log["module"] = self.generate_string(self.generate_integer(1, 500))

                case "safety_flag":
                    log["safety_flag"] = self.select_enum(self.dict_params["safety_flags"])

                case "error_code":
                    log["error_code"] = self.select_enum(self.dict_params["error_codes"])

                case "version":
                    log["version"] = f"""{self.generate_integer(0, 5)}.
                                        {self.generate_integer(0, 10)}.
                                        {self.generate_integer(0, 20)}"""

                case "stack" if "error" in log:
                    log["error"]["stack"] = self.generate_string(200)

                case "request_id":
                    log["request_id"] = self.generate_unique_string()

                case "http_status":
                    log["http_status"] = self.generate_integer(100, 599)

                case "latency_ms":
                    log["latency_ms"] = self.generate_integer(0, 100)

                case "duration_ms":
                    log["duration_ms"] = self.generate_integer(0, 100)

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
        self.input_params = self.verify_input_params()
        self.dict_params = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, invalid_logs
