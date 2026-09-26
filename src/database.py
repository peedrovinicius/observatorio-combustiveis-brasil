from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    url: str


def get_database_settings() -> DatabaseSettings:
    load_dotenv()
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://combustiveis:combustiveis@localhost:5432/combustiveis",
    )
    return DatabaseSettings(url=url)
