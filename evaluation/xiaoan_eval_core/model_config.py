"""Three evaluators share one explicit, file-owned model configuration."""
from __future__ import annotations

from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[2] / "evaluation_multimodels" / ".env"
PROVIDERS = ("claude", "gpt", "gemini", "deepseek")


def read_env(path: Path | None = None) -> dict[str, str]:
    source = path or ENV_PATH
    if not source.is_file():
        raise ValueError(f"缺少共享评估配置：{source}")
    values = {}
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name.strip()] = value
    return values


def required(name: str, values: dict[str, str] | None = None) -> str:
    value = (read_env() if values is None else values).get(name, "").strip()
    if not value:
        raise ValueError(f"请在 evaluation_multimodels/.env 设置 {name}")
    return value


def model(name: str, requested: str | None = None, *, values=None) -> str:
    value = required(name, values)
    if any(c.isspace() for c in value) or "," in value:
        raise ValueError(f"{name} 必须是单个模型 ID")
    if requested and requested != value:
        raise ValueError(f"模型 {requested} 与共享 .env 的 {name}={value} 冲突")
    return value


def matrix_models(provider: str, *, judge: bool = False, values=None) -> tuple[str, ...]:
    if provider not in PROVIDERS:
        raise ValueError(f"评估仅支持 {PROVIDERS}")
    config = read_env() if values is None else values
    tiers = ("JUDGE",) if judge else ("LATEST", "SECOND")
    return tuple(model(f"XIAOAN_{provider.upper()}_{tier}_MODEL", values=config) for tier in tiers)


def validate_matrix_model(provider: str, requested: str, *, judge=False) -> str:
    if requested not in matrix_models(provider, judge=judge):
        raise ValueError(f"模型 {requested} 不在共享 .env 的 {provider} {'judge' if judge else 'answer'} 配置中")
    return requested


def configured_models(values=None) -> set[str]:
    config = read_env() if values is None else values
    return {v.strip() for k, v in config.items()
            if k.startswith("XIAOAN_") and k.endswith("_MODEL") and v.strip()}


def provider_for_model(selected: str, values=None) -> str:
    config = read_env() if values is None else values
    for provider in PROVIDERS:
        if any(config.get(f"XIAOAN_{provider.upper()}_{tier}_MODEL", "").strip() == selected
               for tier in ("LATEST", "SECOND", "JUDGE")):
            return provider
    if selected.startswith("claude"):
        return "claude"
    if selected.startswith("gemini"):
        return "gemini"
    if selected.startswith("deepseek"):
        return "deepseek"
    if selected.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "gpt"
    raise ValueError(f"无法确定模型 {selected} 的厂商；请在共享 .env 的系列模型字段中配置")


def client_config(selected: str, values=None) -> dict[str, str]:
    config = read_env() if values is None else values
    if selected not in configured_models(config):
        raise ValueError(f"模型 {selected} 未在共享 .env 中配置")
    provider = provider_for_model(selected, config)
    family = "OPENAI" if provider == "gpt" else provider.upper()
    defaults = {"CLAUDE": "https://api.anthropic.com/v1", "GEMINI": "https://globalai.vip/v1beta", "DEEPSEEK": "https://api.deepseek.com", "OPENAI": "https://api.openai.com/v1"}
    base_url = (config.get(f"XIAOAN_{family}_BASE_URL", "").strip() or defaults[family]).rstrip("/")
    return {"api_key": required(f"XIAOAN_{family}_API_KEY", config), "base_url": base_url}


def runtime_options(values=None) -> dict[str, object]:
    """读取矩阵并发与 provider 限流；显式 CLI 参数可覆盖这些值。"""
    config = read_env() if values is None else values
    def positive(name: str, default: int) -> int:
        raw = config.get(name, '').strip()
        value = int(raw) if raw else default
        if value < 1:
            raise ValueError(f'{name} 必须大于等于 1')
        return value
    limits = {provider: positive(f'XIAOAN_{provider.upper()}_MAX_CONCURRENCY', 2)
              for provider in PROVIDERS}
    return {
        'subject_concurrency': positive('XIAOAN_SUBJECT_CONCURRENCY', 2),
        'judge_concurrency': positive('XIAOAN_JUDGE_CONCURRENCY', 3),
        'max_in_flight': positive('XIAOAN_MAX_IN_FLIGHT', 3),
        'per_provider_concurrency': limits,
    }
