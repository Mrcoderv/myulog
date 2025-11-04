from generator import GenerateLog


class AgenticGenerator(GenerateLog):
    def __init__(
        self,
        fields: list[str],
        seed: int,
        size: int,
        input_params: list[str] | None,
        valid_params: list[str] | None,
    ) -> None:
        super().__init__(fields, size, seed, valid_params)

        self.parser_versions = ["1.0.0", "1.1.0", "2.0.0"]
        self.input_params = input_params if input_params else []

        self.step_kinds = [
            "plan_created",
            "tool_selected",
            "step",
            "guardrails",
        ]
        self.statuses = ["success", "retry", "timeout", "failed"]
        self.messages = {
            "failed": [
                "Tool execution failed.",
                "Step execution failed.",
                "Workflow execution failed.",
            ],
            "timeout": [
                "Tool execution timed out.",
                "Step execution timed out.",
                "Workflow execution timed out.",
            ],
        }
        self.input_output_summary = [
            {
                "input": "Classify the image and return the label.",
                "output": "The image is classified as a cat.",
            },
            {
                "input": "Translate the text to French.",
                "output": "The text is translated to French.",
            },
            {
                "input": "Summarize the article in a few sentences.",
                "output": "The article is summarized in a few sentences.",
            },
            {
                "input": "Extract the keywords from the text.",
                "output": "The keywords are extracted from the text.",
            },
            {
                "input": "Generate a response to the user's query.",
                "output": "The response to the user's query is generated.",
            },
        ]
        self.error_codes = [f"E{str(i).zfill(3)}" for i in range(1, 13)]
        self.list_of_tools = [
            "web_search",
            "image_generation",
            "text_completion",
            "data_analysis",
            "code_execution",
        ]

        self.param_dict = {}

    def generate_log_entries(self) -> list[dict]:
        logs = []
        for _ in range(self.size):
            input_output = self.select_enum(self.input_output_summary)
            log_entry = {
                # NB: Agentic records in this seed do not include top-level timestamp;
                # raw mirror will inject @timestamp for consistency with sample raw shape.
                "meta": {},
                "step_kind": self.select_enum(self.step_kinds),
                "workflow_id": self.generate_unique_string(),
                "step_id": self.generate_unique_string(),
                "tool_name": self.select_enum(self.list_of_tools),
                "input_summary": input_output["input"],
                "output_summary": input_output["output"],
                "status": self.select_enum(self.statuses),
            }

            if log_entry["status"] in ["failed", "timeout"]:
                log_entry["error"] = {"message": self.select_enum(self.messages[log_entry["status"]])}
            if self.input_params:
                log_entry = self.generate_option_params(log_entry)

            log_entry["meta"]["raw_message"] = self.generate_raw_messages(log_entry)
            logs.append(log_entry)
        return logs

    def generate_option_params(self, log: dict) -> dict:
        for param in self.input_params:
            match param:
                case "parse_timestamp":
                    log["meta"]["parse_timestamp"] = self.generate_timestamp()
                case "parser_version":
                    log["meta"]["parser_version"] = self.select_enum(self.parser_versions)
                case "parent_step_id":
                    log["parent_step_id"] = self.generate_unique_string()
                case "plan_id":
                    log["plan_id"] = self.generate_unique_string()
                case "duration_ms":
                    log['duration_ms'] = self.generate_float(0.0, 500.0)
                case "cost":
                    log["cost"] = {
                        "tokens_in": self.generate_integer(0, 10000),
                        "tokens_out": self.generate_integer(0, 10000),
                        "est_cost_usd": self.generate_float(0.0, 10.0),
                    }
                case "level":
                    log["level"] = self.select_enum(self.param_dict["levels"])
                case "category":
                    log["category"] = "agentic"
                case "sub_category":
                    log["sub_category"] = self.select_enum(self.param_dict["sub_categories"])
                case "safety_flag":
                    log["safety_flag"] = self.select_enum(self.param_dict["safety_flags"])
                case "outcome":
                    if log["status"] in ["failed","retry"]:
                        log["outcome"] = "failure"
                    elif log["status"] in ["success","timeout"]:
                        log["outcome"] = log["status"]
                    else:
                        log["outcome"] = self.select_enum(["cancelled","running","pending"])

                case "error_code":
                    log["error_code"] = self.select_enum(self.error_codes)
                case "ranked_tools":
                    n = self.generate_integer(1, len(self.list_of_tools))
                    ranked_tools = self.random.sample(self.list_of_tools, n) if n > 0 else []
                    log["ranked_tools"] = ranked_tools
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

    def generate_raw_messages(self, log: dict) -> str:
        message = ""
        duration = log.get("duration_ms", self.generate_float(0.0, 500.0))
        param_dict = self.load_param_dict(["levels","sub_categories","safety_flags"])

        level = log.get("level",  self.select_enum(param_dict["levels"]))
        match log["step_kind"]:
            case "plan_created":
                message =  f"{log['meta'].get('parse_timestamp',self.generate_timestamp())} {log['input_summary']}"
            case "tool_selected":
                message =  f"Tool selector ranked {len(log['tool_name'])} , selected {' '.join(log['tool_name'])} ({duration}ms)."
            case "step":
                costs = log.get("cost",{"tokens_in":self.generate_integer(0,10000),
                                        "tokens_out":self.generate_integer(0,10000),
                                        "est_cost_usd":self.generate_float(0.0,10.0)})
                
                messages = [f"[{level.upper()}] {log['input_summary']} duration {duration}ms.",
                            f"{log.get('sub_category',self.select_enum(param_dict['sub_categories']))} inference : {duration*1000}s {costs['tokens_in']} token in ,{costs['tokens_out']} token out , cost {costs['est_cost_usd']}."]
                message = self.select_enum(messages)
            case "guardrails":
                flags = log.get("safety_flag",[self.select_enum(param_dict["safety_flags"])])
                message =  f"[{level.upper()}] , flags {' '.join(flags)} applied - {log['output_summary']}."
            case _:
                pass

        return message

    def run(self) -> tuple[list[dict], list[dict]]:
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entries()
        invalid_logs = self.generate_log_entries()

        # remove one random field from invalid to make them invalid
        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]
        return valid_logs, invalid_logs
