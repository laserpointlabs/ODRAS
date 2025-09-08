from typing import Optional
from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Camunda BPM Configuration
    camunda_base_url: str = "http://localhost:8080"

    # Application Configuration
    api_base_url: str = "http://localhost:8000"
    environment: str = "development"
    log_level: str = "INFO"

    # Installation Configuration for Organizational Namespaces
    # These values are loaded from environment variables with INSTALLATION_ prefix
    installation_organization: str = Field(
        default="ODRAS Development", alias="INSTALLATION_ORGANIZATION"
    )
    installation_base_uri: str = Field(
        default="http://odras.local", alias="INSTALLATION_BASE_URI"
    )  # Override this for production!
    installation_prefix: str = Field(default="odras", alias="INSTALLATION_PREFIX")
    installation_type: str = Field(
        default="development", alias="INSTALLATION_TYPE"
    )  # navy, airforce, army, industry, research, etc.
    installation_program_office: str = Field(
        default="Development", alias="INSTALLATION_PROGRAM_OFFICE"
    )

    # Namespace URI Templates
    namespace_core_template: str = "{base_uri}/core#{entity}"
    namespace_domain_template: str = "{base_uri}/{domain}#{entity}"
    namespace_program_template: str = "{base_uri}/{program}/core#{entity}"
    namespace_project_template: str = "{base_uri}/{program}/{project}#{entity}"
    namespace_se_template: str = "{base_uri}/se/{se_domain}#{entity}"
    namespace_mission_template: str = "{base_uri}/mission/{mission_type}#{entity}"
    namespace_platform_template: str = "{base_uri}/platform/{platform_type}#{entity}"

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # ignore unrelated environment variables
    )
