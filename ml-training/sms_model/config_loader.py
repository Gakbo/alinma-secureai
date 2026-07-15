"""
Configuration loader -- single source of truth for the training pipeline.
All scripts read config/training_config.yaml through this module, so model
choice, hyperparameters, imbalance strategy, and augmentation are all
changeable without touching Python source (upgrade requirement #2).
"""
import os
import yaml

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "training_config.yaml")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _validate(cfg)
    return cfg


def resolve_model(cfg: dict, override_key: str = None) -> dict:
    """Return the selected model entry {key, hf_name, description, ...}."""
    key = override_key or cfg.get("selected_model")
    models = cfg.get("models", {})
    if key not in models:
        raise KeyError(
            f"Model key '{key}' not found in config. "
            f"Available: {list(models.keys())}"
        )
    entry = dict(models[key])
    entry["key"] = key
    return entry


def _validate(cfg: dict):
    for section in ("models", "training", "imbalance"):
        if section not in cfg:
            raise ValueError(f"Config missing required section: '{section}'")
    if cfg.get("selected_model") not in cfg["models"]:
        raise ValueError(
            f"selected_model '{cfg.get('selected_model')}' is not defined "
            f"under models: {list(cfg['models'].keys())}"
        )


if __name__ == "__main__":
    cfg = load_config()
    model = resolve_model(cfg)
    print(f"Config OK. Selected model: {model['key']} -> {model['hf_name']}")
    print(f"Candidates for benchmark: {cfg.get('benchmark', {}).get('candidates')}")
