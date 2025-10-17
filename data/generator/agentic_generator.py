from logging import Logger

from generator import GenerateLog


class AgenticGenerator(GenerateLog):
    def __init__(self, fields : list[str], seed: int, size: int,
                 option_params : list[str] | None = None)-> None:
        super().__init__(fields, size, seed)
        self.logger = Logger(__name__)
        self.parser_versions = ["1.0.0", "1.1.0", "2.0.0"]
        self.step_kinds = ["session_start",
                            "plan_created",
                            "tool_selected",
                            "step",
                            "stream_start",
                            "guardrails",
                            "cost",
                            "cache"
                        ]
        self.statuses = ["success", "retry", "timeout", "failed"]
        self.messages = {
            "failed" : ["Tool execution failed.", 
                        "Step execution failed.", 
                        "Workflow execution failed."
                        ],
            "timeout" : ["Tool execution timed out.",
                        "Step execution timed out.",
                        "Workflow execution timed out."
                        ],
        }
        self.input_output_summary = [{"input": "Classify the image and return the label.",
                                     "output": "The image is classified as a cat."
                                     },
                                     {"input": "Translate the text to French.",
                                      "output": "The text is translated to French."
                                      },
                                     {"input": "Summarize the article in a few sentences.",
                                      "output": "The article is summarized in a few sentences."
                                      },
                                     {"input": "Extract the keywords from the text.",
                                      "output": "The keywords are extracted from the text."
                                      },
                                     {"input": "Generate a response to the user's query.",
                                      "output": "The response to the user's query is generated."
                                      }
                                    ]
        self.error_codes = [
                                "E001",
                                "E002",
                                "E003",
                                "E004",
                                "E005",
                                "E006",
                                "E007",
                                "E008",
                                "E009",
                                "E010",
                                "E011",
                                "E012"
                            ]
        self.outcomes = ["success", "failed"]
        self.safety_flags = ["llm", "cv", "pii", "security"]
        self.category = [
                        "auth",
                        "network",
                        "data",
                        "model",
                        "service",
                        "system",
                        "storage",
                        "scheduler",
                        "deployment",
                        "security",
                        "third_party"
                        ]
        self.levels = ["info", "warn", "error"]
        self.option_params = option_params if option_params else []

        self.valid_params = {
            "parse_timestamp",
            "parser_version",
            "parent_step_id",
            "plan_id",
            "duration_ms",
            "cost",
            "level",
            "category",
            "safety_flag",
            "outcome",
            "error_code"
        }

        self.verify_option_params()

    def generate_log_entries(self) -> list[dict]:
        """Generate a list of log entries."""
        logs = []
        for _ in range(self.size):
            input_output = self.select_enum(self.input_output_summary)
            log_entry = {
                "meta": {
                    "raw_message": self.generate_string(100),
                },
                "step_kind": self.select_enum(self.step_kinds),
                "workflow_id": self.generate_unique_string(),
                "step_id": self.generate_unique_string(),
                "tool_name": self.generate_string(10),
                "input_summary" : input_output["input"],
                "output_summary": input_output["output"],
                "status" : self.select_enum(["success", "retry", "timeout", "failed"]),
            }
            
            if log_entry["status"] in ["failed", "timeout"] :
                log_entry["error"] = {
                    "message": self.select_enum(self.messages[log_entry["status"]])
                }
            logs.append(log_entry)

        return logs
    
    def verify_option_params(self)-> None:
        for param in self.option_params:
            if param not in self.valid_params:
                self.logger.warning(f"Unknown option param: {param}")
    
    def generate_option_params(self,log:dict)-> dict:
        for param in self.option_params:
           
            if param == "parse_timestamp":
               log["meta"]["parse_timestamp"] = self.generate_timestamp()

            elif param == "parser_version":
               log["meta"]["parser_version"] = self.select_enum(self.parser_versions)

            elif param == "parent_step_id":
                log["parent_step_id"] = self.generate_unique_string()

            elif param == "plan_id":
                log["plan_id"] = self.generate_unique_string()

            elif param == "duration_ms":
                log["duration_ms"] = self.generate_float(0.0,500.0)

            elif param == "cost":
                log["cost"] = {
                    "tokens_in": self.generate_integer(0,10000),
                    "tokens_out": self.generate_integer(0,10000),
                    "est_cost_usd": self.generate_float(0.0,10.0)
                }
            elif param == "level":
                log["level"] = self.select_enum(self.levels)

            elif param == "category":
                log["category"] = self.select_enum(self.category)

            elif param == "safety_flag":
                log["safety_flag"] = self.select_enum(self.safety_flags)

            elif param == "outcome":
                log["outcome"] = self.select_enum(self.outcomes)

            elif param == "error_code":
                log["error_code"] = self.select_enum(self.error_codes)
            else:
                continue # skip unknown params, already logged in verify_option_params

        return log
    
    def run(self)-> tuple[list[dict], list[dict]]:
        valid_logs = self.generate_log_entries()
        invalid_logs = self.generate_log_entries()

        # apply option params after we mutate invalid_logs 
        # (so both valid and invalid get same shape)
        if self.option_params:
            valid_logs = [self.generate_option_params(log) for log in valid_logs]
            invalid_logs = [self.generate_option_params(log) for log in invalid_logs]

        # remove fields from invalid_logs (so they become invalid)
        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, invalid_logs