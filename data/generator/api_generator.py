from typing import List

from generator import GenerateLog


class GenerateAPILog(GenerateLog):
    def __init__(
        self,
        fields: List[str],
        size: int,
        seed: int,
        input_params: List[str] | None,
        valid_params: List[str] | None,
    ) -> None:
        super().__init__(fields, size, seed, valid_params)
        self.input_params = input_params if input_params else []

        # Load from vocab for consistent outcomes
        self.outcomes = self.load_from_vocab(["outcomes"])[0]

        # --- API definitions ---
        self.param_dict = {}
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
            "apprunner_event",
        ]
        self.endpoints = [
            "/api/v1/resource",
            "/api/v1/resource/2",
            "/api/v1/resource/2/action",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/login",
            "/logout",
            "/checkout",
            "/update",
            "/get",
            "/query",
            "/action",
        ]

        # --- AppRunner templates ---
        self.repo_types = ["Source", "ECR"]
        self.repos = [
            "https://github.com/ExampleOrg/website_chatbot",
            "https://github.com/ExampleOrg/profile-pulse",
            "https://github.com/ExampleOrg/LMS_AI_AGENT",
        ]
        self.app_events = [
            "[AppRunner] Deployment Artifact: [Repo Type: {repo_type}], [Repository: {repo_url}], [Branch: {branch}],\
                  [SourceDirectory: /]",
            "[AppRunner] Deployment with ID : {deploy_id} started. Triggering event : {event_type}",
            "[AppRunner] Pulling source code from GITHUB Repository ( {repo_url} ).",
            "[AppRunner] Successfully pulled your application source code.",
            "[AppRunner] Health check is successful. Routing traffic to application.",
            "[AppRunner] Your application stopped or failed to start. See logs for more information.\
                  Container exit code: {exit_code}",
        ]
        self.app_event_types = ["SERVICE_CREATE", "SERVICE_UPDATE", "SERVICE_DEPLOY"]

        # --- Build templates ---
        self.build_templates = [
            "[Build] Downloading {package}-{version}-py3-none-any.whl ({size} kB)",
            "[Build] WARNING: The candidate selected for download or install is a yanked version: '{package}'\
                  candidate (version {version})",
            "[Build] Successfully installed {package}-{version}",
        ]

        # --- Traceback templates ---
        self.traceback_templates = [
            "Traceback (most recent call last):",
            ' File "/usr/local/lib/python3.{pyver}/site-packages/{module}/{submodule}.py", line {line}, in <module>',
            ' File "/usr/local/lib/python3.{pyver}/site-packages/{module}/{submodule}.py", line {line2}, in {func}',
            "{errtype}: {errmsg}",
        ]

    def generate_log_entry(self):
        # Each "size" iteration will produce one event group deterministically
        logs = []
        i = 0  # iteration counter for timestamp offsets

        # Keep track of messages to prevent duplicates
        used_messages = set()

        while len(logs) < self.size:
            # Randomly decide: API-style log or AppRunner-style
            mode = self.select_enum(["apprunner", "build", "traceback", "http"])
            base_ts = self.generate_timestamp(base_date=None, offset_s=3600 * i)

            group_logs = []

            # Determine group size dynamically
            if mode == "apprunner":
                group_size = self.random.randint(3, 6)
            elif mode == "build":
                group_size = self.random.randint(2, 5)
            elif mode == "traceback":
                group_size = self.random.randint(3, 6)
            else:
                group_size = 1

            ts_group = self.generate_timestamp_group(base_ts, group_size)

            def unique_message(template_func):
                # Generate a unique message, retry if duplicate
                attempt = 0
                while True:
                    message = template_func()
                    if message not in used_messages:
                        used_messages.add(message)
                        return message
                    attempt += 1
                    if attempt > 10:  # fail-safe
                        return message

            # --- AppRunner group ---
            if mode == "apprunner":
                repo_type = self.select_enum(self.repo_types)
                repo_url = self.select_enum(self.repos)
                branch = self.select_enum(["main", "dev", "release"])
                deploy_id = self.generate_unique_string()[:16]
                event_type = self.select_enum(self.app_event_types)
                exit_code = self.generate_integer(0, 137)

                templates = self.random.sample(self.app_events, k=len(self.app_events))  # unique templates
                for t in ts_group:
                    # Pick a template function to generate a message
                    def tpl_func(template=templates.pop(0)):
                        return template.format(
                            repo_type=repo_type,
                            repo_url=repo_url,
                            branch=branch,
                            deploy_id=deploy_id,
                            event_type=event_type,
                            exit_code=exit_code,
                        )

                    message = unique_message(tpl_func)
                    group_logs.append(
                        self.generate_option_params(
                            {
                                "meta": {"raw_message": message},
                                "timestamp": t,
                                "event_type": "apprunner_event",
                                "service": "AppRunner",
                                "env": self.select_enum(self.env),
                                "outcome": self.select_enum(["success", "failure"]),
                                "repository": repo_url,
                                "repo_type": repo_type,
                                "branch": branch,
                                "event": event_type,
                            }
                        )
                    )

            # --- Build group ---
            elif mode == "build":
                for t in ts_group:

                    def tpl_func():
                        pkg = self.generate_string(self.generate_integer(5, 10))
                        version = f"{self.generate_integer(0, 3)}.{self.generate_integer(0, 10)}\
                            .{self.generate_integer(0, 5)}"
                        size_kb = self.generate_integer(50, 400)
                        template = self.random.choice(self.build_templates)
                        return template.format(package=pkg, version=version, size=size_kb)

                    message = unique_message(tpl_func)
                    group_logs.append(
                        self.generate_option_params(
                            {
                                "meta": {"raw_message": message},
                                "timestamp": t,
                                "event_type": "build",
                                "service": "BuildSystem",
                                "env": self.select_enum(self.env),
                                "outcome": self.select_enum(["success", "failure"]),
                            }
                        )
                    )

            # --- Realistic Traceback group ---
            elif mode == "traceback":
                # Pre-generate shared traceback context
                pyver = self.generate_integer(8, 11)
                module = self.select_enum(["git", "click", "app", "server", "service", "db"])
                submodule = self.select_enum(["core", "cmd", "init", "main"])
                func = self.select_enum(["refresh", "run", "load_config", "<module>"])
                errtype = self.select_enum(["ModuleNotFoundError", "ImportError", "RuntimeError", "ValueError"])
                submodule = self.select_enum(["core", "cmd", "init", "main", "tasks", "loader"])
                func = self.select_enum(["refresh", "run", "load_config", "start", "execute"])
                line = self.generate_integer(50, 900)
                errmsg = self.select_enum(
                    [
                        "No module named 'uvicorn'",
                        "Failed to connect to DB",
                        "Invalid import path",
                        "Invalid configuration",
                        "Unhandled exception occurred",
                    ]
                )

                # Generate 2–4 realistic stack frames
                frame_count = self.random.randint(2, 4)
                frames = []
                for _ in range(frame_count):
                    frame = (
                        f'  File "/usr/local/lib/python3.{pyver}/site-packages/{module}/{submodule}.py", '
                        f"line {line}, in {func}"
                    )
                    frame = frame.format(
                        pyver=pyver,
                        module=module,
                        submodule=submodule,
                        func=func,
                        line=line,
                    )
                    frames.append(frame)

                # Build complete traceback lines
                traceback_lines = ["Traceback (most recent call last):"] + frames + [f"{errtype}: {errmsg}"]
                # Emit one traceback line per timestamp in the group
                for index, t in enumerate(ts_group):
                    # Clamp index so we don't overflow traceback_lines
                    line_index = index if index < len(traceback_lines) else len(traceback_lines) - 1
                    message = traceback_lines[line_index]

                    message = unique_message(lambda m=message: m)

                    group_logs.append(
                        self.generate_option_params(
                            {
                                "meta": {"raw_message": message},
                                "timestamp": t,
                                "event_type": "exception",
                                "service": self.generate_service_name(),
                                "env": self.select_enum(self.env),
                                "outcome": "failure",
                                "module": f"{module}.{submodule}",
                                "error_type": errtype,
                            }
                        )
                    )

            # --- HTTP / API default ---
            else:
                # Generate realistic message
                def tpl_func():
                    return self.generate_message(domain="api", word_count=20)

                message = unique_message(tpl_func)
                log_entry = {
                    "meta": {"raw_message": message},
                    "timestamp": base_ts,
                    "event_type": self.select_enum(self.event_types),
                    "service": self.generate_service_name(),
                    "env": self.select_enum(self.env),
                    "outcome": self.select_enum(self.outcomes),
                }
                if log_entry["event_type"] in ["http_request", "http_response"]:
                    log_entry["endpoint"] = self.select_enum(self.endpoints)
                    log_entry["action"] = self.select_enum(self.actions)

                # Add error on failures
                if log_entry.get("outcome") == "failure":
                    err_type = self.select_enum(self.errors)
                    choice_1 = {"type": err_type, "message": self.error_messages[err_type]}
                    choice_2 = {"type": err_type}
                    log_entry["error"] = self.select_enum([choice_1, choice_2])
                # --- Optional custom params ---
                group_logs.append(self.generate_option_params(log_entry))

            # Add group logs but do not exceed requested size
            remaining = self.size - len(logs)
            logs.extend(group_logs[:remaining])
            i += 1  # increment iteration for timestamp offset

        return logs

    # Optional param logic
    def generate_option_params(self, log: dict) -> dict:
        for param in self.input_params:
            match param:
                case "parse":
                    log["meta"]["parse_name"] = self.generate_string(10)
                    log["meta"]["parser_version"] = self.select_enum(["1.0.0", "1.1.0", "2.0.0"])
                    log["meta"]["pattern_id"] = self.generate_unique_string()
                    log["meta"]["confidence"] = self.generate_float(0, 1)
                case "level":
                    log["level"] = self.select_enum(self.param_dict.get("levels", ["info", "warn", "error"]))
                case "category":
                    log["category"] = self.select_enum(self.param_dict.get("categories", ["system", "api"]))
                case "sub_category":
                    log["sub_category"] = self.select_enum(self.param_dict.get("sub_categories", ["auth", "build"]))
                case "component":
                    log["component"] = self.generate_string(self.generate_integer(4, 15))
                case "module":
                    log["module"] = self.generate_string(self.generate_integer(4, 20))
                case "safety_flag":
                    log["safety_flag"] = self.select_enum(self.param_dict.get("safety_flags", ["ok", "warning"]))
                case "error_code":
                    log["error_code"] = self.select_enum(self.param_dict.get("error_codes", ["E001", "E002"]))
                case "version":
                    major = self.generate_integer(0, 5)
                    minor = self.generate_integer(0, 10)
                    patch = self.generate_integer(0, 20)
                    log["version"] = f"{major}.{minor}.{patch}"
                case "stack" if "error" in log:
                    log["error"]["stack"] = self.generate_string(200)
                case "stack":
                    log["stack_trace"] = self.generate_stacktrace()
                case "request_id":
                    log["request_id"] = self.generate_unique_string()
                case "http_status":
                    log["http_status"] = self.generate_integer(100, 599)
                case "latency_ms":
                    log["latency_ms"] = self.generate_float(0, 5000)
                case "duration_ms":
                    log["duration_ms"] = self.generate_float(0, 5000)
                case _:
                    continue
        return log

    def verify_input_params(self) -> list[str]:
        verified = []
        for param in self.input_params:
            if self.verify_option_params(param, self.valid_params):
                verified.append(param)
            else:
                self.logger.warning(f"Unknown option param: {param}")
        return verified

    def run(self):
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        # Randomly remove a field to simulate malformed logs
        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, invalid_logs
