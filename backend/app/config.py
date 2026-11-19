import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    llm_provider: str
    ollama_url: str
    ollama_model: str
    openai_api_key: str
    openai_model: str
    headless: bool
    frontend_dist: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "testpilot.db"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"


def get_settings() -> Settings:
    return Settings(
        data_dir=Path(os.getenv("TESTPILOT_DATA_DIR", ROOT_DIR / "data")),
        llm_provider=os.getenv("TESTPILOT_LLM", "none").lower(),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        headless=os.getenv("TESTPILOT_HEADLESS", "1") != "0",
        frontend_dist=ROOT_DIR / "frontend" / "dist",
    )
