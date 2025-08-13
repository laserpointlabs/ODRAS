from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpassword"
    fuseki_url: str = "http://localhost:3030/odras"
    ollama_url: str = "http://localhost:11434"

    llm_provider: str = "openai"  # openai | ollama
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None

    collection_name: str = "odras_requirements"

    class Config:
        env_file = ".env"
        case_sensitive = False




