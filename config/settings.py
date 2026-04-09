from pydantic_settings import BaseSettings, SettingsConfigDict
from qdrant_client import QdrantClient
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "lexagent"
    postgres_user: str = "lexagent"
    postgres_password: str = "lexagent_secret"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "eu_ai_act"
    qdrant_api_key: str = ""

    google_api_key: str = ""
    llm_model: str = "gemini-1.5-flash"
    embed_model: str = "models/gemini-embedding-001"

    log_level: str = "INFO"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_qdrant_client(self) -> QdrantClient:
        kwargs = {"host": self.qdrant_host, "port": self.qdrant_port}
        if self.qdrant_api_key:
            kwargs = {"url": self.qdrant_host, "api_key": self.qdrant_api_key}
        return QdrantClient(**kwargs)

    def get_llm(self, streaming: bool = False) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=self.llm_model,
            temperature=0.0,
            api_key=self.google_api_key
        )

    def get_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        return GoogleGenerativeAIEmbeddings(
            model=self.embed_model,
            google_api_key=self.google_api_key
        )


settings = Settings()
