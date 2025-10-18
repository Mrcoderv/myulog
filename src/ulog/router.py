"""ULog Domain Router — dataset-tuned (strict component mapping + disambiguation)."""

from __future__ import annotations

import json
import re
from typing import Optional

from .parsers import AgenticParser, BaseParser, CoreAPIParser, CVParser, LLMParser

# --------- Utilities ---------

RE_JSON_MSG_KEYS = ("@message", "message", "msg", "text", "log")

# LangChain / AgentExecutor style lines (tool-using agents)
LANGCHAIN_LINE = re.compile(r'(^|\s)(Action(?: Input)?|Observation|Thought|Final Answer):\s*')
LANGCHAIN_ENTER = re.compile(r'^\s*>\s+.+')

# First [Component] token at line start/anywhere
RE_FIRST_BRACKET = re.compile(r'\[([A-Za-z0-9\.\-_]+)\]')

# Strong endpoint/path hints
RE_OPENAI_ENDPOINT = re.compile(r'/v1/(chat/completions|completions|embeddings)\b', re.IGNORECASE)
RE_CV_INFER = re.compile(r'(^|[\s"])POST\s+/infer\b|/infer\b', re.IGNORECASE)

# ---- Core/API signals (deployment/build/runtime/web infra) ----
RE_CORE_APPRUNNER = re.compile(
    r'\[AppRunner\]|\bECR\b|arn:aws:|Deployment Artifact|Health ?check|Liveness|Readiness|'
    r'Routing traffic|Scaling (up|down)|Rollback|Service (deletion|update|deploy) started|'
    r'quota exceeded|ThrottlingException|ExpiredToken|AccessDenied|manifest unknown|'
    r'no matching manifest',
    re.IGNORECASE,
)

RE_CORE_WEB = re.compile(
    r'\bUvicorn\b|\bGunicorn\b|\bFastAPI\b|\bASGI\b|\bStarlette\b|\bOpenAPI\b|/docs/?\b|/openapi\.json\b|'
r'Waiting for application startup|Application startup complete|lifespan|Started server process|Finished server process',
    re.IGNORECASE,
)

RE_CORE_BUILD = re.compile(
    r'\[Build\]|requirements\.txt|pip (check|install)|wheel|No space left on device|'
    r'HASHES FROM THE REQUIREMENTS FILE|uvloop build failed|hash sha256:|'
    r'No matching distribution found|yanked version|conflicting dependencies|pip check failed',
    re.IGNORECASE,
)

RE_CORE_RUNTIME = re.compile(
    r'(?:^Traceback \(most recent call last\):)|click\.exceptions|BadParameter|NoSuchOption|'
    r'Usage: .* \[OPTIONS\]|Try .* --help|pydantic(_core)?\.|ValidationError|dotenv|\.env|'
    r'yaml\.|YAML|Address already in use|PermissionError: \[Errno 13\]|SIGTERM|graceful|'
    r'readiness|liveness|/metrics\b|ConnectionRefusedError|requests\.exceptions|'
    r'JSONDecodeError|ValueError: Invalid .*URL|Invalid DATABASE_URL|'
    r'(?:urllib3|urllib)\.|ConnectTimeout|SSLCertVerificationError|SSL: CERTIFICATE_VERIFY_FAILED|'
    r'alembic|sqlalchemy|OperationalError|FileNotFoundError|RuntimeError: Event loop is closed',
    re.IGNORECASE,
)

RE_CORE_GIT = re.compile(
    r'git\.exc\.|GitCommandNotFound|InvalidGitRepositoryError|Pulling source code from GITHUB',
    re.IGNORECASE,
)

RE_CORE_HTTPLOG = re.compile(
    r'"\s*(GET|POST|PUT|DELETE|PATCH)\s+/[^\s]*\s+HTTP/(1\.[01]|2)"\s+\d{3}\b',
    re.IGNORECASE,
)

def _looks_core(msg: str) -> bool:
    """Heuristics for Core/API (deploy/build/runtime/web infra)."""
    return (
        RE_CORE_APPRUNNER.search(msg)
        or RE_CORE_WEB.search(msg)
        or RE_CORE_BUILD.search(msg)
        or RE_CORE_RUNTIME.search(msg)
        or RE_CORE_GIT.search(msg)
        or RE_CORE_HTTPLOG.search(msg)
    )


# ---- LLM/CV/Agentic keyword sets ----

RE_LLM_KEYWORDS = re.compile(
    r'(?:\bMAX_BATCH_TOTAL_TOKENS\b|vLLM|OpenAI-compatible|Llama\.cpp|llama-server|GGML_ASSERT|ggml|'
    r'TritonIS\b|text-generation-inference\b|TGI\b|KVCache\b|kv_cache\b|paged\s+KV|speculative|'
    r'\btool_calls\b|context_window\b|ttft\b|tps\b|/v1/(chat/completions|completions|embeddings)\b|'
    r'embeddings\b|nucleus\(top_p=|\btop_p\b|\btemperature\b|presence_penalty|frequency_penalty|'
    r'prompt_tokens|completion_tokens|json_schema\b|min_p\b)',
    re.IGNORECASE,
)

RE_CV_KEYWORDS = re.compile(
    r'(OpenCV|cv2|TensorRT|ONNXRuntime|OpenVINO|COCO mAP|mAP@|NMS\(|\bIoU\b|keypoints|RTSP|Letterbox|'
    r'Pose|Segmentation|DeepSORT|ByteTrack|Jetson|Tesseract|Invalid resolution 0 dpi|'
    r'(-215:Assertion failed)|!ssize\.empty\(\)|inv_scale_x\s*>\s*0|cuDNN|CUDNN_STATUS|'
    r'CUDA (out of memory|illegal memory access))',
    re.IGNORECASE,
)

RE_AGENTIC_KEYWORDS = re.compile(
    r'(plan_created|replan|finalize_without|vector_search|low_recall|hybrid|bm25|dense|'
    r'\bTool\b|\[Tool\]|\btool_calls\b|shell_sandbox|HumanGate|SelfHeal|Handoff|Aggregator|'
    r'deliver|artifacts|approval|multi_agent|handoff|arbiter)',
    re.IGNORECASE,
)


# --------- Component lists (direct mapping) ---------

# Clearly AGENTIC in your dataset
AGENTIC_COMPONENTS = {
    "Agent", "Policies", "Registry", "Capabilities", "Input", "Extractor", "Memory",
    "Planner", "Plan", "Graph", "Selector", "Tool", "Observe", "Verifier", "RAG",
    "Aggregator", "Guard", "Coder", "Reviewer", "Arbiter", "Handoff", "SelfHeal",
    "Fallback", "HumanGate", "Structured", "Security", "Sanitizer", "Compliance",
    "Audit", "Events", "Diagnostics", "Cost", "Cache", "RateLimit", "Retry",
    "Timeout", "Cancel", "CircuitBreaker", "Deliver", "Output", "Formatter",
    "Orchestrator", "Researcher", "Sampler", "JSON", "Shutdown",
}

# Clearly CV in your dataset
CV_COMPONENTS = {
    "Data", "Preproc", "Aug", "Model", "ONNXRuntime", "OpenVINO", "TensorRT",
    "Infer", "Post", "OCR", "Track", "Pose", "Eval", "Serve", "gRPC", "Config",
    "CLI", "Train", "Dbg", "Security", "Privacy", "HW", "Env",
}

# Clearly LLM in your dataset (includes infra + OpenAI-compatible HTTP layer)
LLM_COMPONENTS = {
    "Serve", "Router", "Auth", "Tokenizer", "Model", "Loader", "Quant", "KVCache",
    "Context", "vLLM", "Batcher", "Speculative", "HTTP", "Stream", "JSON",
    "ToolCall", "Safety", "PII", "RateLimit", "Prompt", "Cache", "RAG", "Sampler",
    "Lang", "Metrics", "HW", "Distributed", "MPS", "Tracing", "Audit", "Guardrails",
    "Policies", "Embeddings", "TLS", "Telemetry", "TritonIS", "TGI", "Scheduler",
    "ColdStart", "Cleanup", "Shutdown", "Llama.cpp", "ggml", "Plugins", "Web",
    "SSE", "Monitor", "gRPC", "Logger", "Train", "LoRA", "QLoRA",
    "Optimizer", "Trainer", "Checkpoint", "Eval", "Merge", "Export",
}

# Components potentially ambiguous across domains
AMBIGUOUS = {
    "Serve", "HTTP", "gRPC", "Router", "Metrics", "JSON", "RAG", "Sampler",
    "Policies", "Model", "Config", "HW", "Cache", "Prompt", "Lang", "Train",
    "Eval", "Shutdown",
}


def _extract_message(raw: str) -> str:
    """Return the message string for routing.

    1) If input is a JSON object, pick a well-known message field.
    2) If JSON fails but looks like concatenated JSON ({}{}...), try to parse the first object.
    3) Otherwise, return the raw string unchanged.
    """
    # Fast path: plain JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            for k in RE_JSON_MSG_KEYS:
                v = obj.get(k)
                if isinstance(v, str) and v:
                    return v
    except Exception:
        pass

    # Heuristic: concatenated JSON objects — parse the first complete one
    if raw and raw.lstrip().startswith("{") and "}{" in raw:
        depth = 0
        for i, ch in enumerate(raw):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    chunk = raw[: i + 1]
                    try:
                        obj = json.loads(chunk)
                        if isinstance(obj, dict):
                            for k in RE_JSON_MSG_KEYS:
                                v = obj.get(k)
                                if isinstance(v, str) and v:
                                    return v
                    except Exception:
                        break
                    finally:
                        break

    return raw or ""


def _first_component(msg: str) -> Optional[str]:
    m = RE_FIRST_BRACKET.search(msg)
    return m.group(1) if m else None


def _looks_llm(msg: str) -> bool:
    # Strong endpoint/path hints
    if RE_OPENAI_ENDPOINT.search(msg):
        return True

    # Keyword signatures
    if RE_LLM_KEYWORDS.search(msg):
        # Hard guard: if embeddings/LLM terms appear *with* clear CV libs, prefer not LLM.
        if (re.search(r'\bembeddings\b', msg, re.IGNORECASE) or 
            "tokens_in" in msg or "tokens_out" in msg) and RE_CV_KEYWORDS.search(msg):
            return False
        return True

    # gRPC/Serve/HTTP with explicit LLM hints
    if "[gRPC]" in msg or "[Serve]" in msg or "[HTTP]" in msg:
        if "LLM" in msg or "Inference service READY" in msg or "model=llm" in msg or "chat/completions" in msg:
            return True
    return False


def _looks_cv(msg: str) -> bool:
    if RE_CV_INFER.search(msg):
        return True
    if RE_CV_KEYWORDS.search(msg):
        return True
    return False


def _looks_agentic(msg: str) -> bool:
    if LANGCHAIN_ENTER.search(msg) or LANGCHAIN_LINE.search(msg):
        return True
    if RE_AGENTIC_KEYWORDS.search(msg):
        return True
    return False


class DomainRouter:
    """Deterministic router: prefer [Component] mapping first, then content-based disambiguation."""

    def __init__(self) -> None:
        self._parsers = {
            "core_api": CoreAPIParser(),
            "llm": LLMParser(),
            "agentic": AgenticParser(),
            "cv": CVParser(),
        }

    def detect_domain(self, raw_message: str) -> Optional[str]:
        return self._route_domain(raw_message)

    def route(self, raw_message: str, domain_hint: Optional[str] = None) -> BaseParser:
        if domain_hint:
            if domain_hint not in self._parsers:
                raise ValueError(
                    f"Invalid domain hint: {domain_hint}. "
                    f"Valid domains: {list(self._parsers.keys())}"
                )
            return self._parsers[domain_hint]
        return self._parsers[self._route_domain(raw_message)]

    # --------- Core ---------

    def _route_domain(self, raw_message: str) -> str:
        msg = _extract_message(raw_message).strip()
        if not msg:
            return "core_api"

        # 0) Agent-style lines without [Component] (LangChain/AgentExecutor)
        if LANGCHAIN_ENTER.search(msg) or LANGCHAIN_LINE.search(msg):
            return "agentic"

        comp = _first_component(msg)

        # 1) No [Component] -> use keyword/endpoint heuristics
        if not comp:
            # Prefer explicit infra/agent signals before generic LLM metrics to avoid edge FPs
            if _looks_core(msg):
                return "core_api"
            if _looks_agentic(msg):
                return "agentic"
            if _looks_cv(msg):
                return "cv"
            if _looks_llm(msg):
                return "llm"
            return "core_api"

        # 2) Direct mapping by component when NOT ambiguous
        if comp in AGENTIC_COMPONENTS and comp not in AMBIGUOUS:
            return "agentic"
        if comp in CV_COMPONENTS and comp not in AMBIGUOUS:
            return "cv"
        if comp in LLM_COMPONENTS and comp not in AMBIGUOUS:
            return "llm"

        # 3) Disambiguation for ambiguous components
        if comp in AMBIGUOUS or comp in LLM_COMPONENTS or comp in AGENTIC_COMPONENTS:
            # Path & metric-based hard signals
            if re.search(r'/v1/(chat/completions|completions|embeddings)\b', msg, re.IGNORECASE) \
               or re.search(r'\b(ttft|tokens_in|tokens_out|tps=|MAX_BATCH_TOTAL_TOKENS)\b', msg, re.IGNORECASE):
                # Guard against CV contamination
                if RE_CV_KEYWORDS.search(msg):
                    pass
                else:
                    return "llm"

            if re.search(r'(^|[\s"])POST\s+/infer\b|/infer\b', msg, re.IGNORECASE) or RE_CV_KEYWORDS.search(msg):
                return "cv"

            # Infra / deployment / runtime / web server => Core/API
            if _looks_core(msg):
                return "core_api"

            # General priority (dataset-informed): LLM > CV > Agentic
            if _looks_llm(msg):
                return "llm"
            if _looks_cv(msg):
                return "cv"
            if _looks_agentic(msg):
                return "agentic"

            # Special cases
            if comp == "Model" and RE_CV_KEYWORDS.search(msg):
                return "cv"
            if comp == "RAG" and re.search(r'(vector_search|hybrid|bm25|dense|low_recall)', msg, re.IGNORECASE):
                return "agentic"

            # Default for ambiguous: LLM (fits dataset distribution)
            return "llm"

        # 4) Unknown component -> generic heuristics
        if _looks_core(msg):
            return "core_api"
        if _looks_agentic(msg):
            return "agentic"
        if _looks_cv(msg):
            return "cv"
        if _looks_llm(msg):
            return "llm"

        return "core_api"


# Default instance & helper
_DEFAULT_ROUTER = DomainRouter()

def route_domain(raw_message: str) -> str:
    return _DEFAULT_ROUTER._route_domain(raw_message)
