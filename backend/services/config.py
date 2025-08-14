from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpassword"
    fuseki_url: str = "http://localhost:3030/odras"
    fuseki_user: Optional[str] = None
    fuseki_password: Optional[str] = None
    ollama_url: str = "http://localhost:11434"

    llm_provider: str = "openai"  # openai | ollama
    llm_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None

    collection_name: str = "odras_requirements"
    
    # File Storage Configuration
    storage_backend: str = "minio"  # local | minio | postgresql
    
    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "odras-files"
    minio_secure: bool = False

    # PostgreSQL Configuration  
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "odras"
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    
    # Local Storage Configuration
    local_storage_path: str = "./storage/files"

    class Config:
        env_file = ".env"
        case_sensitive = False




