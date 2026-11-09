"""
Configuration and Environment Settings for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent System)
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class Agent2Settings(BaseModel):
    """Runtime configuration for Target Market Researcher Agent."""

    agent_name: str = "Target Market Researcher"
    agent_id: str = "agent_2"
    version: str = "0.1.0"

    # Agent Reach CLI settings
    agent_reach_bin: str = Field(
        default_factory=lambda: os.getenv("AGENT_REACH_BIN", "agent-reach")
    )
    agent_reach_timeout: int = int(os.getenv("AGENT_REACH_TIMEOUT", "45"))

    # Web & Scraping settings
    request_timeout: int = int(os.getenv("HTTP_TIMEOUT", "15"))
    default_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (scalyn.si MarketScout)"
    )

    # Search & Discovery defaults
    supported_platforms: list[str] = [
        "linkedin",
        "x",
        "reddit",
        "web",
    ]
    min_match_score: int = 5
    max_prospects_per_run: int = 15

    # Storage paths
    dossier_output_dir: Path = OUTPUT_DIR

    # LLM Settings (for synthesis and scoring)
    model_name: str = os.getenv("GROWWITHAI_MODEL", "gemini-2.5-flash")


settings = Agent2Settings()
