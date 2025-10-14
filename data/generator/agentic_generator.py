from logging import Logger

from ULog.data.generator.generator import GenerateLog


class AgenticGenerator(GenerateLog):
    def __init__(self, fields : list[str], seed: int, size: int,option_params : list[str] = []):
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
        self.erros_codes = [
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
        self.outcomes = ["success", "failure"]
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
        self.option_params = option_params

    def generate_log(self):
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
                "status" : self.select_enum(["success", "error", "partial_success"]),
            }
            logs.append(log_entry)
            if log_entry["status"] in ["failed", "timeout"] :
                log_entry["error"] = {
                    "message": self.select_enum(self.messages[log_entry["status"]])
                }

        return logs
    
    def generate_option_params(self,log:dict):
        for param in self.option_params:
           
            if param == "parse_timestamp":
               log["meta"]["parse_timestamp"] = self.generate_timestamp()
            elif param == "parser_version":
               log["meta"]["parser_version"] = self.select_enum(self.parser_versions)
            elif param == "parent_step_id":
                log["parent_step_id"] = self.generate_unique_string()
            elif param == "plan_id":
                log["ranked_tools"] = [{"item":self.generate_string(10)} 
                                        for _ in range(self.generate_integer(1,5))
                                        ]
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
                log["error_code"] = self.select_enum(self.erros_codes)
            else:
                self.logger.warning(f"Unknown option param: {param}")
                continue

        return log
    
    def run(self):
        valid_logs = self.generate_log()
        unvalid_logs = self.generate_log()
        if self.option_params:
            valid_logs = [self.generate_option_params(log) for log in valid_logs]
            unvalid_logs = [self.generate_option_params(log) for log in unvalid_logs]

        for log in unvalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]
        
        if self.option_params:
            valid_logs = [self.generate_option_params(log) for log in valid_logs]
            unvalid_logs = [self.generate_option_params(log) for log in unvalid_logs]

        return valid_logs, unvalid_logs