import yaml
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_all_prompts():
    with open("config/prompts.yaml", "r") as f:
        return yaml.safe_load(f)

def load_prompt(node_name: str):
    prompts = _load_all_prompts()
    return prompts.get(node_name)