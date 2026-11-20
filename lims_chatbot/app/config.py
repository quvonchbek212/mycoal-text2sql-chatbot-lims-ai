"""Konfiguratsiya — barcha sozlamalar muhit o'zgaruvchilaridan (.env) o'qiladi."""
from __future__ import annotations

import pathlib
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


SCHEMA_DIR = pathlib.Path(__file__).resolve().parent.parent / "schema"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Chat LLM (vLLM, OpenAI-mos API) ---
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_api_key: str = "dummy"
    vllm_model: str = "gemma4-31b"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1500
    llm_timeout: float = 120.0

    # --- PostgreSQL (READ-ONLY foydalanuvchi) ---
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "limsdb"
    db_user: str = "lims-user"
    db_password: str = ""
    db_include_schemas: str = "public"
    # Sxema manbasi. Yaratish: python -m lims_chatbot.tools.generate_ddl
    schema_file: str = str(SCHEMA_DIR / "schema.json")
    ddl_file: str = str(SCHEMA_DIR / "ddl.sql")

    # --- Suhbat xotirasi (alohida PostgreSQL, YOZISH huquqi bilan) ---
    # LIMS bazasi read-only — tarix boshqa bazaga yoziladi. CHAT_DB_HOST bo'sh
    # bo'lsa xotira jarayon ichida qoladi (qayta ishga tushsa yo'qoladi).
    chat_db_host: str = ""
    chat_db_port: int = 5432
    chat_db_name: str = ""
    chat_db_user: str = ""
    chat_db_password: str = ""
    chat_db_schema: str = "public"
    # Jadvallar: <prefix>_sessions, <prefix>_messages — bazadagi boshqa
    # chatbot jadvallari (masalan chat_history) bilan to'qnashmaydi.
    chat_db_table_prefix: str = "lims_chatbot"

    # --- Xavfsizlik / cheklovlar ---
    sql_row_limit: int = 500
    max_rows_to_model: int = 20  # xulosa LLM iga beriladigan satrlar (ro'yxatni kod qo'shadi)
    statement_timeout_ms: int = 15000
    schema_char_budget: int = 24000
    schema_refresh_seconds: int = 600
    llm_health_timeout: float = 10.0
    llm_max_retries: int = 1
    max_sql_attempts: int = 3

    # --- Xizmat ---
    cors_allow_origins: str = "*"
    # HTTP Basic login/parol (barcha endpointlar uchun). Bo'sh bo'lsa — barcha
    # so'rov rad etiladi (himoya jimgina o'chib qolmasin).
    api_username: str = ""
    api_password: str = ""
    # Optional separate accounts; session history is isolated by authenticated account.
    api_accounts: dict[str, str] = Field(default_factory=dict, repr=False)

    @property
    def include_schemas_list(self) -> list[str]:
        return [s.strip() for s in self.db_include_schemas.split(",") if s.strip()]

    @property
    def db_source(self) -> str:
        """Snapshot identity, without credentials."""
        return f"{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def chat_db_enabled(self) -> bool:
        return bool(self.chat_db_host and self.chat_db_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
