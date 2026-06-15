import os
import re
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def csv_ids(value: str) -> list[int]:
    ids = []
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids

def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

def env_bool(name: str, default: str = "false") -> bool:
    return env(name, default).lower() in {"1", "true", "yes", "sim", "on", "ligado"}

def env_float(name: str, default: str) -> float:
    try:
        return float(env(name, default))
    except Exception:
        return float(default)

def env_int(name: str, default: str) -> int:
    try:
        return int(env(name, default))
    except Exception:
        return int(default)

def normalize_provider(value: str) -> str:
    value = (value or "openrouter").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    aliases = {
        "ollama_cloud": "ollama_cloud",
        "ollama": "ollama_cloud",
        "ollama_nuvem": "ollama_cloud",
        "olhama_cloud": "ollama_cloud",
        "olhama": "ollama_cloud",
        "ollama_local": "ollama_local",
        "olhama_local": "ollama_local",
        "open_router": "openrouter",
        "openrouter": "openrouter",
        "groq": "groq",
        "custom": "custom",
    }
    return aliases.get(value, value)

def looks_placeholder(value: str) -> bool:
    v = (value or "").lower()
    return not v or "coloque_" in v or "sua_" in v or "api_key" in v

def resolve_llm_config() -> tuple[str, str, str, str]:
    manual_base = env("LLM_BASE_URL")
    manual_key = env("LLM_API_KEY")
    manual_model = env("LLM_MODEL")

    if manual_base and manual_model:
        if manual_key.startswith("http"):
            manual_key = ""
        return "manual", manual_base.rstrip("/"), manual_key, manual_model

    provider = normalize_provider(env("LLM_PROVIDER", "openrouter"))

    if provider == "openrouter":
        return provider, env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"), env("OPENROUTER_API_KEY"), env("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    if provider == "groq":
        return provider, env("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"), env("GROQ_API_KEY"), env("GROQ_MODEL", "llama-3.1-8b-instant")
    if provider == "ollama_cloud":
        return provider, env("OLLAMA_CLOUD_BASE_URL", "https://api.ollama.com/v1").rstrip("/"), env("OLLAMA_CLOUD_API_KEY"), env("OLLAMA_CLOUD_MODEL", "llama3.2")
    if provider == "ollama_local":
        return provider, env("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434/v1").rstrip("/"), env("OLLAMA_LOCAL_API_KEY"), env("OLLAMA_LOCAL_MODEL", "llama3.2")
    if provider == "custom":
        return provider, env("CUSTOM_LLM_BASE_URL").rstrip("/"), env("CUSTOM_LLM_API_KEY"), env("CUSTOM_LLM_MODEL")

    raise RuntimeError("LLM_PROVIDER inválido. Use: openrouter, groq, ollama_cloud, ollama_local ou custom.")

@dataclass(frozen=True)
class Settings:
    discord_token: str
    owner_ids: list[int]
    guild_id: int | None
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout: float
    llm_temperature: float
    llm_max_tokens: int
    openrouter_site_url: str
    openrouter_app_name: str
    search_enabled: bool
    search_provider: str
    search_max_results: int
    search_timeout: float
    brave_search_api_key: str
    tavily_api_key: str
    bot_prefix: str
    database_path: str
    embed_color: int
    max_history_messages: int
    app_name: str
    app_version: str
    log_level: str
    vision_model: str  # modelo de visão — vazio = desativado

_provider, _base_url, _api_key, _model = resolve_llm_config()

settings = Settings(
    discord_token=env("DISCORD_TOKEN"),
    owner_ids=csv_ids(env("OWNER_IDS")),
    guild_id=int(env("GUILD_ID")) if env("GUILD_ID").isdigit() else None,
    llm_provider=_provider,
    llm_base_url=_base_url,
    llm_api_key=_api_key,
    llm_model=_model,
    llm_timeout=env_float("LLM_TIMEOUT", "25"),
    llm_temperature=env_float("LLM_TEMPERATURE", "0.35"),
    llm_max_tokens=env_int("LLM_MAX_TOKENS", "700"),
    openrouter_site_url=env("OPENROUTER_SITE_URL"),
    openrouter_app_name=env("OPENROUTER_APP_NAME", env("APP_NAME", "REPLICANT")),
    search_enabled=env_bool("SEARCH_ENABLED", "true"),
    search_provider=env("SEARCH_PROVIDER", "duckduckgo").lower(),
    search_max_results=env_int("SEARCH_MAX_RESULTS", "5"),
    search_timeout=env_float("SEARCH_TIMEOUT", "12"),
    brave_search_api_key=env("BRAVE_SEARCH_API_KEY"),
    tavily_api_key=env("TAVILY_API_KEY"),
    bot_prefix=env("BOT_PREFIX", "r!"),
    database_path=env("DATABASE_PATH", "data/bot.sqlite3"),
    embed_color=int(env("EMBED_COLOR", "5865F2"), 16),
    max_history_messages=env_int("MAX_HISTORY_MESSAGES", "20"),
    app_name=env("APP_NAME", "REPLICANT"),
    app_version=env("APP_VERSION", "0.5.0"),
    log_level=env("LOG_LEVEL", "INFO"),
    vision_model=env("VISION_MODEL", ""),
)

if not settings.discord_token:
    raise RuntimeError("DISCORD_TOKEN não configurado no .env")

if not settings.llm_base_url or not settings.llm_model:
    raise RuntimeError("LLM não configurado. Ajuste LLM_PROVIDER ou LLM_BASE_URL/LLM_MODEL no .env")

if settings.llm_provider in {"openrouter", "groq", "ollama_cloud"} and looks_placeholder(settings.llm_api_key):
    raise RuntimeError(f"{settings.llm_provider} precisa de API key real no .env")
