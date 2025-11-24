import importlib.util
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gen_dir = PROJECT_ROOT / "data" / "generator"
api_mod = load_module("api_generator", gen_dir / "api_generator.py")
llm_mod = load_module("llm_generator", gen_dir / "llm_generator.py")
cv_mod = load_module("cv_generator", gen_dir / "cv_generator.py")
agent_mod = load_module("agentic_generator", gen_dir / "agentic_generator.py")

GenerateAPILog = api_mod.GenerateAPILog
GenerateLLMLog = llm_mod.GenerateLLMLog
GenerateCVLog = cv_mod.GenerateCVLog
AgenticGenerator = agent_mod.AgenticGenerator

print("Creating generators with seed=123")
api = GenerateAPILog(fields=["nonexistent_field"], size=2, seed=123, input_params=None, valid_params=None)
llm = GenerateLLMLog(fields=["nonexistent_field"], size=2, seed=123, input_params=None, valid_params=None)
cv = GenerateCVLog(fields=["nonexistent_field"], size=2, seed=123, input_params=None, valid_params=None)
agent = AgenticGenerator(fields=["nonexistent_field"], seed=123, size=2, input_params=None, valid_params=None)

v_api, i_api = api.run()
v_llm, i_llm = llm.run()
v_cv, i_cv = cv.run()
v_agent, i_agent = agent.run()

print("\nAPI sample:")
print(v_api[0])
print("\nLLM sample:")
print(v_llm[0])
print("\nCV sample:")
print(v_cv[0])
print("\nAgentic sample:")
print(v_agent[0])
